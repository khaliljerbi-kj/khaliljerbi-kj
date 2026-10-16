import { Badge } from "@/components/ui/badge";
import { quartierBySlug } from "@/lib/quartiers";
import { FEATURE_LABELS, type SearchCriteria } from "@/lib/types";
import { euros } from "@/lib/utils";

export function CriteriaChips({ criteria }: { criteria: SearchCriteria }) {
  const chips: { label: string; tone?: "ai" | "secondary" }[] = [];
  const c = criteria;
  if (c.budget_max) chips.push({ label: `≤ ${euros(c.budget_max)} CC` });
  if (c.rooms_min) chips.push({ label: c.rooms_min === 1 ? "Studio+" : `${c.rooms_min} pièces+` });
  if (c.surface_min) chips.push({ label: `${c.surface_min} m²+` });
  if (c.furnished !== null) chips.push({ label: c.furnished ? "Meublé" : "Vide" });
  if (c.commute) chips.push({ label: `≤ ${c.commute.max_minutes} min · ${c.commute.destination}` });
  c.ambiance.forEach((a) => chips.push({ label: a, tone: "ai" }));
  if (c.nightlife_nearby) chips.push({ label: "bars à proximité", tone: "ai" });
  c.must_have.forEach((f) => chips.push({ label: `✓ ${FEATURE_LABELS[f]}` }));
  c.nice_to_have.forEach((f) => chips.push({ label: `+ ${FEATURE_LABELS[f]}`, tone: "secondary" }));
  c.quartiers.forEach((s) => chips.push({ label: quartierBySlug(s)?.nom ?? s }));
  if (!c.quartiers.length)
    c.suggested_quartiers.forEach((s) => chips.push({ label: `~ ${quartierBySlug(s)?.nom ?? s}`, tone: "secondary" }));
  c.arrondissements.forEach((a) => chips.push({ label: `${a}e arr.` }));
  if (c.dpe_max) chips.push({ label: `DPE ≤ ${c.dpe_max}` });

  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {chips.map((chip) => (
        <Badge key={chip.label} variant={chip.tone ?? "outline"}>
          {chip.label}
        </Badge>
      ))}
    </div>
  );
}
