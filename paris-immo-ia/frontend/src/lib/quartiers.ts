import data from "@shared/quartiers.json";

export type Quartier = (typeof data.quartiers)[number];

export const QUARTIERS: Quartier[] = [...data.quartiers].sort(
  (a, b) => a.arrondissement - b.arrondissement || a.nom.localeCompare(b.nom, "fr"),
);

export const quartierBySlug = (slug: string) => QUARTIERS.find((q) => q.slug === slug);
