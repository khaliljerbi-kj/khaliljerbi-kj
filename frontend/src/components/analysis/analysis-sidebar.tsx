"use client";

import { AlertTriangle, MapPin, X } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import type { EstimateResponse } from "@/lib/api";
import { formatEurM2, formatPct } from "@/lib/format";
import { cn } from "@/lib/utils";
import { HistoryChart } from "./history-chart";
import { HorizonTable } from "./horizon-table";
import { ProjectionChart } from "./projection-chart";

interface Props {
  open: boolean;
  data: EstimateResponse | null;
  loading: boolean;
  error: string | null;
  onClose: () => void;
}

export function AnalysisSidebar({ open, data, loading, error, onClose }: Props) {
  const first = data?.history[0]?.price;
  const change5y = data && first ? data.current_price_m2 / first - 1 : null;

  return (
    <aside
      aria-label="Analyse de la zone"
      className={cn(
        "bg-background/95 fixed inset-x-0 bottom-0 z-20 flex max-h-[75vh] flex-col border-t backdrop-blur transition-transform duration-300",
        "md:inset-x-auto md:top-0 md:right-0 md:bottom-0 md:max-h-none md:w-[440px] md:border-t-0 md:border-l",
        open ? "translate-y-0 md:translate-x-0" : "translate-y-full md:translate-x-full md:translate-y-0",
      )}
    >
      <header className="flex items-start justify-between gap-3 border-b px-4 py-3">
        <div className="min-w-0">
          <div className="text-muted-foreground flex items-center gap-1.5 text-xs">
            <MapPin className="size-3.5" />
            {data ? `Paris ${data.location.arrondissement}${data.location.arrondissement === 1 ? "er" : "e"}` : "Sélection"}
            {data?.is_mock && (
              <Badge variant="outline" className="ml-1">
                Données simulées
              </Badge>
            )}
          </div>
          <h2 className="truncate text-base font-semibold">{data?.location.label ?? "Chargement…"}</h2>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} aria-label="Fermer le panneau">
          <X />
        </Button>
      </header>

      <div className={cn("flex-1 space-y-3 overflow-y-auto p-4 transition-opacity", loading && data && "opacity-50")}>
        {error && (
          <div className="flex items-start gap-2 rounded-md border border-[#d03b3b]/50 bg-[#d03b3b]/10 p-3 text-sm">
            <AlertTriangle className="mt-0.5 size-4 shrink-0 text-[#d03b3b]" />
            <div>
              <div className="font-medium">Estimation indisponible</div>
              <div className="text-muted-foreground text-xs">{error}</div>
            </div>
          </div>
        )}

        {!data && loading && <SidebarSkeleton />}

        {data && (
          <>
            <Card>
              <CardHeader>
                <CardDescription>Prix actuel estimé</CardDescription>
                <div className="text-3xl font-semibold tracking-tight">{formatEurM2(data.current_price_m2)}</div>
                {change5y !== null && (
                  <div className="text-muted-foreground text-xs">
                    <span className="text-foreground font-medium">{formatPct(change5y)}</span> sur 5 ans · vol. hist.{" "}
                    {formatPct(data.calibration.hist_sigma).replace("+", "")}/an
                  </div>
                )}
              </CardHeader>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Historique (5 ans)</CardTitle>
                <CardDescription>Prix moyen au m², trimestriel</CardDescription>
              </CardHeader>
              <CardContent>
                <HistoryChart data={data.history} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Projections Monte Carlo (GBM)</CardTitle>
                <CardDescription>
                  {data.calibration.n_paths.toLocaleString("fr-FR")} trajectoires par scénario · bandes du scénario médian
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <ProjectionChart data={data.projection} />
                <HorizonTable horizons={data.horizons} />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Hypothèses des scénarios</CardTitle>
              </CardHeader>
              <CardContent>
                <dl className="space-y-2 text-xs">
                  {data.scenarios.map((s) => (
                    <div key={s.key}>
                      <dt className="flex justify-between font-medium">
                        <span>{s.label}</span>
                        <span className="text-muted-foreground tabular-nums">
                          μ {formatPct(s.mu)} · σ {formatPct(s.sigma).replace("+", "")}
                        </span>
                      </dt>
                      <dd className="text-muted-foreground">{s.description}</dd>
                    </div>
                  ))}
                </dl>
              </CardContent>
            </Card>
          </>
        )}
      </div>
    </aside>
  );
}

function SidebarSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-24 w-full" />
      <Skeleton className="h-52 w-full" />
      <Skeleton className="h-80 w-full" />
    </div>
  );
}
