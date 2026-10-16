from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Ambiance = Literal["calme", "festif", "familial", "branche", "etudiant", "chic", "authentique", "verdoyant"]
Feature = Literal[
    "fibre", "ascenseur", "balcon", "parking", "cave", "lave_vaisselle", "animaux", "sur_cour", "meuble"
]
TravelMode = Literal["transit", "walking", "bicycling"]
DpeLetter = Literal["A", "B", "C", "D", "E", "F", "G"]


class Commute(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str = Field(description="Lieu tel que formulé par l'utilisateur, ex. 'Télécom Paris'")
    max_minutes: int = Field(ge=5, le=180)
    mode: TravelMode = "transit"


class SearchCriteria(BaseModel):
    """Objet de recherche strict produit par le LLM et consommé par le moteur de matching."""

    model_config = ConfigDict(extra="forbid")

    budget_max: int | None = Field(None, description="Loyer charges comprises maximum, en euros/mois")
    surface_min: float | None = Field(None, description="Surface minimale en m²")
    rooms_min: int | None = Field(None, description="Nombre de pièces minimum (studio = 1, T2 = 2)")
    furnished: bool | None = Field(None, description="True = meublé, False = vide, null = indifférent")
    commute: Commute | None = None
    quartiers: list[str] = Field(
        default_factory=list, description="Slugs de micro-quartiers explicitement demandés par l'utilisateur"
    )
    suggested_quartiers: list[str] = Field(
        default_factory=list, description="Slugs de micro-quartiers déduits du lifestyle (utilisateur ne connaissant pas Paris)"
    )
    arrondissements: list[int] = Field(default_factory=list)
    ambiance: list[Ambiance] = Field(default_factory=list)
    nightlife_nearby: bool = Field(False, description="Veut des bars / restos sympas à proximité")
    must_have: list[Feature] = Field(default_factory=list, description="Critères éliminatoires")
    nice_to_have: list[Feature] = Field(default_factory=list)
    dpe_max: DpeLetter | None = Field(None, description="Pire DPE accepté")
    floor_min: int | None = None
    knows_paris: bool | None = None
    summary: str = Field("", description="Récapitulatif en une phrase, en français")

    def is_searchable(self) -> bool:
        return any(
            [
                self.budget_max,
                self.commute,
                self.quartiers,
                self.suggested_quartiers,
                self.arrondissements,
                self.ambiance,
                self.surface_min,
                self.rooms_min,
            ]
        )


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=40)
    criteria: SearchCriteria | None = Field(None, description="Critères accumulés lors des tours précédents")


class ExtractionResult(BaseModel):
    reply: str
    criteria: SearchCriteria
    ready_to_search: bool
    missing: list[str] = Field(default_factory=list)


class CommuteInfo(BaseModel):
    destination: str
    minutes: int
    mode: TravelMode
    estimated: bool = Field(description="True si calcul approximatif (pas d'appel Google Maps)")


class ScoreBreakdown(BaseModel):
    label: str
    score: float  # 0-1
    weight: float
    detail: str


class PropertyCard(BaseModel):
    """'Fiche Bien' renvoyée au frontend."""

    id: str
    source: Literal["local", "seloger", "leboncoin"]
    external_url: str | None = None
    title: str
    description: str
    address: str
    quartier: str
    quartier_nom: str
    arrondissement: int
    latitude: float
    longitude: float
    rent_cc: int
    rent_hc: int
    charges: int
    surface: float
    rooms: int
    floor: int
    has_elevator: bool
    furnished: bool
    dpe: DpeLetter
    features: list[Feature]
    photos: list[str]
    match_score: int
    breakdown: list[ScoreBreakdown]
    commute: CommuteInfo | None = None
    why_for_you: str = ""


class ChatResponse(BaseModel):
    reply: str
    criteria: SearchCriteria
    ready_to_search: bool
    matches: list[PropertyCard] = Field(default_factory=list)
    used_external_sources: bool = False
    notes: list[str] = Field(default_factory=list, description="Avertissements (critère assoupli…)")
    llm_provider: str


class AlertCreate(BaseModel):
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    name: str | None = None
    query: str = Field(max_length=4000)
    criteria: SearchCriteria


class AlertOut(BaseModel):
    id: str
    email: str
    min_score: int
    active: bool
