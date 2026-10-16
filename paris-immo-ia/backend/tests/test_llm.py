from app.schemas import ChatMessage, PropertyCard
from app.services.llm import _RemoteProvider


class FakeProvider(_RemoteProvider):
    """Simule la réponse d'un outil forcé (Anthropic tool_use / OpenAI function call)."""

    name = "fake"

    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def _call_tool(self, system, messages, tool, description, schema):
        self.calls.append((tool, messages))
        response = self.responses[tool]
        if isinstance(response, Exception):
            raise response
        return response


MESSAGES = [
    ChatMessage(role="assistant", content="Bonjour !"),
    ChatMessage(role="user", content="Calme mais proche de bars, 1300 € max"),
]


def test_remote_extraction_is_validated_and_history_normalized():
    provider = FakeProvider(
        {
            "enregistrer_recherche": {
                "reply": "Je cible la Butte-aux-Cailles.",
                "ready_to_search": True,
                "criteria": {
                    "budget_max": 1300,
                    "ambiance": ["calme"],
                    "nightlife_nearby": True,
                    "suggested_quartiers": ["butte-aux-cailles", "inconnu"],
                },
            }
        }
    )
    r = provider.extract(MESSAGES, None)
    assert r.criteria.suggested_quartiers == ["butte-aux-cailles"]
    _, sent = provider.calls[0]
    assert sent[0]["role"] == "user", "l'accueil assistant ne doit pas ouvrir l'historique"
    assert "Critères accumulés" in sent[0]["content"]


def test_remote_failure_falls_back_to_heuristic():
    provider = FakeProvider({"enregistrer_recherche": RuntimeError("timeout")})
    r = provider.extract(MESSAGES, None)
    assert r.criteria.budget_max == 1300 and r.criteria.nightlife_nearby


def test_pitches_fill_missing_ids_with_template(client):
    cards = client.post(
        "/api/chat", json={"messages": [{"role": "user", "content": "calme, bars, 1300 € max, fibre"}]}
    ).json()["matches"]
    cards = [PropertyCard.model_validate(c) for c in cards]
    provider = FakeProvider({"rediger_pitchs": {"pitches": [{"id": cards[0].id, "text": "Texte LLM."}]}})
    pitches = provider.pitches(MESSAGES, _criteria(), cards)
    assert pitches[0] == "Texte LLM."
    assert all(pitches[1:]), "les biens sans texte LLM reçoivent le gabarit"


def _criteria():
    from app.schemas import SearchCriteria

    return SearchCriteria(budget_max=1300, ambiance=["calme"], nightlife_nearby=True)
