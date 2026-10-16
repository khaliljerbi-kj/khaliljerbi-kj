import { Building, Clock, ExternalLink, MapPin, Sofa, Sparkles, Train } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Card } from "@/components/ui/card";
import { FEATURE_LABELS, type Dpe, type PropertyCardData } from "@/lib/types";
import { cn, euros } from "@/lib/utils";

const DPE_COLORS: Record<Dpe, string> = {
  A: "bg-[#009c6d] text-white",
  B: "bg-[#52b153] text-white",
  C: "bg-[#a5cc74] text-stone-900",
  D: "bg-[#f4e70f] text-stone-900",
  E: "bg-[#f0b40f] text-stone-900",
  F: "bg-[#eb8235] text-white",
  G: "bg-[#d7221f] text-white",
};

const SOURCE_LABEL = { local: "Exclusivité", seloger: "SeLoger · simulé", leboncoin: "Leboncoin · simulé" };
const MODE_LABEL: Record<string, string> = { transit: "en transports", walking: "à pied", bicycling: "à vélo" };

function scoreTone(score: number) {
  if (score >= 90) return "text-emerald-700 border-emerald-600/40 bg-emerald-50";
  if (score >= 75) return "text-primary border-primary/30 bg-secondary";
  return "text-amber-800 border-amber-500/40 bg-amber-50";
}

function Datum({ label, value, children }: { label: string; value?: React.ReactNode; children?: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-muted/60 px-3 py-2">
      <dt className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="mt-0.5 font-medium">{value ?? children}</dd>
    </div>
  );
}

export function PropertyCard({ property: p, rank }: { property: PropertyCardData; rank: number }) {
  const extras = p.features.filter((f) => f !== "meuble");
  return (
    <Card className="gap-0 overflow-hidden py-0">
      <div className="relative h-36 bg-gradient-to-br from-primary to-[oklch(0.45_0.08_250)] text-primary-foreground">
        {p.photos[0] ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={p.photos[0]} alt={p.title} className="absolute inset-0 size-full object-cover" />
        ) : (
          <div className="absolute inset-0 flex items-end p-4">
            <span className="font-serif text-3xl font-semibold opacity-90">{p.quartier_nom}</span>
          </div>
        )}
        <div className="absolute left-3 top-3 flex gap-2">
          <Badge className="bg-background/90 text-foreground">#{rank}</Badge>
          <Badge variant={p.source === "local" ? "ai" : "secondary"}>{SOURCE_LABEL[p.source]}</Badge>
        </div>
        <div
          className={cn(
            "absolute right-3 top-3 rounded-full border px-2.5 py-1 text-sm font-semibold shadow-sm",
            scoreTone(p.match_score),
          )}
          title="Score de correspondance"
        >
          {p.match_score} % match
        </div>
      </div>

      <div className="space-y-4 p-5">
        <div>
          <h3 className="font-serif text-lg font-semibold leading-snug">{p.title}</h3>
          <p className="mt-1 flex items-start gap-1 text-sm text-muted-foreground">
            <MapPin className="mt-0.5 size-3.5 shrink-0" />
            <span>
              {p.quartier_nom} · {p.arrondissement}
              <sup>e</sup> — {p.address}
            </span>
          </p>
        </div>

        <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3 2xl:grid-cols-6">
          <Datum label="Loyer CC" value={euros(p.rent_cc)} />
          <Datum label="Surface" value={`${p.surface} m² · ${p.rooms} p.`} />
          <Datum label="DPE">
            <span className={cn("inline-flex size-6 items-center justify-center rounded font-bold", DPE_COLORS[p.dpe])}>
              {p.dpe}
            </span>
          </Datum>
          <Datum label="Étage">
            <span className="inline-flex items-center gap-1">
              <Building className="size-3.5" /> {p.floor === 0 ? "RDC" : `${p.floor}e`}
              {p.has_elevator && <span className="text-xs text-muted-foreground">· asc.</span>}
            </span>
          </Datum>
          <Datum label="Type">
            <span className="inline-flex items-center gap-1">
              <Sofa className="size-3.5" /> {p.furnished ? "Meublé" : "Vide"}
            </span>
          </Datum>
          <Datum label="Hors charges" value={`${euros(p.rent_hc)} + ${euros(p.charges)}`} />
        </dl>

        {p.commute && (
          <p className="flex items-center gap-2 text-sm">
            <Train className="size-4 text-primary" />
            <span>
              <strong>
                {p.commute.estimated && "≈ "}
                {p.commute.minutes} min
              </strong>{" "}
              {MODE_LABEL[p.commute.mode] ?? ""} jusqu&apos;à {p.commute.destination}
            </span>
          </p>
        )}

        {p.why_for_you && (
          <div className="rounded-xl border border-ai-border bg-ai p-4">
            <p className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-ai-foreground">
              <Sparkles className="size-3.5" /> Pourquoi ce bien est fait pour vous ?
            </p>
            <p className="mt-2 text-sm leading-relaxed">{p.why_for_you}</p>
          </div>
        )}

        {extras.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {extras.map((f) => (
              <Badge key={f} variant="outline">
                {FEATURE_LABELS[f]}
              </Badge>
            ))}
          </div>
        )}

        <details className="group text-sm">
          <summary className="flex cursor-pointer list-none items-center gap-1 text-muted-foreground hover:text-foreground">
            <Clock className="size-3.5" /> Détail du score
          </summary>
          <ul className="mt-3 space-y-2">
            {p.breakdown.map((b) => (
              <li key={b.label}>
                <div className="flex justify-between text-xs">
                  <span className="font-medium">{b.label}</span>
                  <span className="text-muted-foreground">{b.detail}</span>
                </div>
                <div className="mt-1 h-1.5 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-primary" style={{ width: `${Math.round(b.score * 100)}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </details>

        {p.external_url && (
          <a
            href={p.external_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
          >
            Voir l&apos;annonce d&apos;origine <ExternalLink className="size-3.5" />
          </a>
        )}
      </div>
    </Card>
  );
}
