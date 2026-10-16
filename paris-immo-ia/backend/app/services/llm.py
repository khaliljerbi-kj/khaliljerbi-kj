"""Couche LLM : extraction de critères (function calling) et rédaction des fiches.

Deux fournisseurs interchangeables (Anthropic, OpenAI) partagent les mêmes
prompts et le même schéma d'outil, dérivé du modèle Pydantic SearchCriteria.
Sans clé API, un extracteur heuristique prend le relais.
"""

import json
import logging
from copy import deepcopy
from functools import lru_cache
from typing import Any, Protocol


from ..config import get_settings
from ..knowledge.paris import quartiers
from ..schemas import ChatMessage, ExtractionResult, PropertyCard, SearchCriteria
from . import heuristic, pitch
from .prompts import (
    EXTRACTION_TOOL,
    PITCH_SYSTEM_PROMPT,
    PITCH_TOOL,
    extraction_system_prompt,
    pitch_tool_schema,
)

log = logging.getLogger(__name__)


def _inline_refs(schema: dict) -> dict:
    """Remplace les $ref Pydantic par leur définition (schéma plus robuste pour le function calling)."""
    defs = schema.pop("$defs", {})

    def walk(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                return walk(deepcopy(defs[node["$ref"].split("/")[-1]]))
            return {k: walk(v) for k, v in node.items() if k != "title"}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node

    return walk(schema)


@lru_cache
def extraction_tool_schema() -> dict:
    return {
        "type": "object",
        "properties": {
            "reply": {"type": "string", "description": "Message affiché à l'utilisateur"},
            "ready_to_search": {"type": "boolean"},
            "missing": {"type": "array", "items": {"type": "string"}},
            "criteria": _inline_refs(SearchCriteria.model_json_schema()),
        },
        "required": ["reply", "ready_to_search", "criteria"],
    }


def _normalize_history(messages: list[ChatMessage]) -> list[dict]:
    """Les API exigent une alternance stricte commençant par l'utilisateur."""
    out: list[dict] = []
    for m in messages:
        if not out and m.role != "user":
            continue
        if out and out[-1]["role"] == m.role:
            out[-1]["content"] += "\n" + m.content
        else:
            out.append({"role": m.role, "content": m.content})
    return out


def _context_message(previous: SearchCriteria | None) -> str:
    prev = previous.model_dump_json() if previous else "{}"
    return f"Critères accumulés jusqu'ici (JSON) : {prev}"


def _sanitize(raw: dict) -> ExtractionResult:
    criteria = raw.get("criteria") or {}
    known = quartiers()
    for key in ("quartiers", "suggested_quartiers"):
        criteria[key] = [s for s in criteria.get(key) or [] if s in known]
    result = ExtractionResult.model_validate({**raw, "criteria": criteria})
    if not result.criteria.quartiers and not result.criteria.suggested_quartiers:
        result.criteria.suggested_quartiers = heuristic.suggest_quartiers(result.criteria)
    return result


def _user_request(messages: list[ChatMessage]) -> str:
    return "\n".join(m.content for m in messages if m.role == "user")


def _pitch_payload(query: str, criteria: SearchCriteria, cards: list[PropertyCard]) -> str:
    biens = []
    for card in cards:
        q = quartiers().get(card.quartier)
        biens.append(
            {
                "id": card.id,
                "titre": card.title,
                "description": card.description,
                "quartier": card.quartier_nom,
                "arrondissement": card.arrondissement,
                "ambiance_quartier": q.description if q else None,
                "scores_quartier": {"calme": q.calme, "vie_nocturne": q.vie_nocturne, "familial": q.familial} if q else None,
                "lignes": list(q.lignes) if q else [],
                "loyer_cc": card.rent_cc,
                "surface": card.surface,
                "pieces": card.rooms,
                "etage": card.floor,
                "meuble": card.furnished,
                "dpe": card.dpe,
                "equipements": card.features,
                "trajet": card.commute.model_dump() if card.commute else None,
                "score_matching": card.match_score,
            }
        )
    return json.dumps(
        {"demande_locataire": query, "criteres": criteria.model_dump(exclude_defaults=True), "biens": biens},
        ensure_ascii=False,
    )


class LLMProvider(Protocol):
    name: str

    def extract(self, messages: list[ChatMessage], previous: SearchCriteria | None) -> ExtractionResult: ...

    def pitches(self, messages: list[ChatMessage], criteria: SearchCriteria, cards: list[PropertyCard]) -> list[str]: ...


class HeuristicProvider:
    name = "heuristic"

    def extract(self, messages, previous):
        return heuristic.heuristic_extract(messages, previous)

    def pitches(self, messages, criteria, cards):
        return [pitch.template_pitch(criteria, card) for card in cards]


class _RemoteProvider:
    """Logique commune : appel forcé d'un outil, validation, repli heuristique."""

    name = "remote"

    def _call_tool(self, system: str, messages: list[dict], tool: str, description: str, schema: dict) -> dict:
        raise NotImplementedError

    def extract(self, messages, previous):
        history = _normalize_history(messages)
        history[0]["content"] = f"{_context_message(previous)}\n\n{history[0]['content']}"
        try:
            raw = self._call_tool(
                extraction_system_prompt(),
                history,
                EXTRACTION_TOOL,
                "Enregistre les critères de recherche structurés et la réponse à afficher.",
                extraction_tool_schema(),
            )
            return _sanitize(raw)
        except Exception as exc:  # erreur réseau, quota ou sortie invalide
            log.warning("Sortie LLM invalide, repli heuristique : %s", exc)
            return heuristic.heuristic_extract(messages, previous)

    def pitches(self, messages, criteria, cards):
        if not cards:
            return []
        payload = _pitch_payload(_user_request(messages), criteria, cards)
        try:
            raw = self._call_tool(
                PITCH_SYSTEM_PROMPT,
                [{"role": "user", "content": payload}],
                PITCH_TOOL,
                "Enregistre le paragraphe 'Pourquoi ce bien est fait pour vous ?' de chaque bien.",
                pitch_tool_schema(),
            )
            by_id = {p["id"]: p["text"].strip() for p in raw.get("pitches", []) if p.get("text")}
        except Exception as exc:  # erreur réseau, quota ou sortie invalide
            log.warning("Rédaction LLM indisponible, gabarit utilisé : %s", exc)
            by_id = {}
        return [by_id.get(card.id) or pitch.template_pitch(criteria, card) for card in cards]


class AnthropicProvider(_RemoteProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        import anthropic

        self.client = anthropic.Anthropic(api_key=api_key, max_retries=2, timeout=45)
        self.model = model

    def _call_tool(self, system, messages, tool, description, schema):
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=system,
            messages=messages,
            tools=[{"name": tool, "description": description, "input_schema": schema}],
            tool_choice={"type": "tool", "name": tool},
        )
        for block in response.content:
            if block.type == "tool_use" and block.name == tool:
                return dict(block.input)
        raise ValueError("Aucun appel d'outil dans la réponse Anthropic")


class OpenAIProvider(_RemoteProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        import openai

        self.client = openai.OpenAI(api_key=api_key, max_retries=2, timeout=45)
        self.model = model

    def _call_tool(self, system, messages, tool, description, schema):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, *messages],
            tools=[{"type": "function", "function": {"name": tool, "description": description, "parameters": schema}}],
            tool_choice={"type": "function", "function": {"name": tool}},
        )
        calls = response.choices[0].message.tool_calls or []
        for call in calls:
            if call.function.name == tool:
                return json.loads(call.function.arguments)
        raise ValueError("Aucun appel de fonction dans la réponse OpenAI")


@lru_cache
def get_provider() -> LLMProvider:
    s = get_settings()
    choice = s.llm_provider
    if choice == "auto":
        choice = "anthropic" if s.anthropic_api_key else "openai" if s.openai_api_key else "heuristic"
    if choice == "anthropic" and s.anthropic_api_key:
        return AnthropicProvider(s.anthropic_api_key, s.anthropic_model)
    if choice == "openai" and s.openai_api_key:
        return OpenAIProvider(s.openai_api_key, s.openai_model)
    if choice != "heuristic":
        log.warning("LLM_PROVIDER=%s sans clé API : extracteur heuristique utilisé", choice)
    return HeuristicProvider()
