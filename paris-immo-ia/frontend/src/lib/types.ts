// Miroir des modèles Pydantic de backend/app/schemas.py
export type Ambiance = "calme" | "festif" | "familial" | "branche" | "etudiant" | "chic" | "authentique" | "verdoyant";
export type Feature =
  | "fibre"
  | "ascenseur"
  | "balcon"
  | "parking"
  | "cave"
  | "lave_vaisselle"
  | "animaux"
  | "sur_cour"
  | "meuble";
export type Dpe = "A" | "B" | "C" | "D" | "E" | "F" | "G";

export interface SearchCriteria {
  budget_max: number | null;
  surface_min: number | null;
  rooms_min: number | null;
  furnished: boolean | null;
  commute: { destination: string; max_minutes: number; mode: "transit" | "walking" | "bicycling" } | null;
  quartiers: string[];
  suggested_quartiers: string[];
  arrondissements: number[];
  ambiance: Ambiance[];
  nightlife_nearby: boolean;
  must_have: Feature[];
  nice_to_have: Feature[];
  dpe_max: Dpe | null;
  floor_min: number | null;
  knows_paris: boolean | null;
  summary: string;
}

export interface ScoreBreakdown {
  label: string;
  score: number;
  weight: number;
  detail: string;
}

export interface PropertyCardData {
  id: string;
  source: "local" | "seloger" | "leboncoin";
  external_url: string | null;
  title: string;
  description: string;
  address: string;
  quartier: string;
  quartier_nom: string;
  arrondissement: number;
  rent_cc: number;
  rent_hc: number;
  charges: number;
  surface: number;
  rooms: number;
  floor: number;
  has_elevator: boolean;
  furnished: boolean;
  dpe: Dpe;
  features: Feature[];
  photos: string[];
  match_score: number;
  breakdown: ScoreBreakdown[];
  commute: { destination: string; minutes: number; mode: string; estimated: boolean } | null;
  why_for_you: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatResponse {
  reply: string;
  criteria: SearchCriteria;
  ready_to_search: boolean;
  matches: PropertyCardData[];
  used_external_sources: boolean;
  notes: string[];
  llm_provider: string;
}

export const FEATURE_LABELS: Record<Feature, string> = {
  fibre: "Fibre",
  ascenseur: "Ascenseur",
  balcon: "Balcon / extérieur",
  parking: "Parking",
  cave: "Cave",
  lave_vaisselle: "Lave-vaisselle",
  animaux: "Animaux acceptés",
  sur_cour: "Sur cour (calme)",
  meuble: "Meublé",
};
