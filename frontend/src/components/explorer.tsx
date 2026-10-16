"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useRef, useState } from "react";
import { Box, Layers, Loader2 } from "lucide-react";

import { AnalysisSidebar } from "@/components/analysis/analysis-sidebar";
import type { MapSelection } from "@/components/map/price-map";
import { PriceLegend } from "@/components/map/price-legend";
import { Button } from "@/components/ui/button";
import { fetchEstimate, fetchPriceGrid, type EstimateResponse, type PriceGrid } from "@/lib/api";
import { cn } from "@/lib/utils";

// MapLibre touches `window`: render the map on the client only.
const PriceMap = dynamic(() => import("@/components/map/price-map"), {
  ssr: false,
  loading: () => (
    <div className="text-muted-foreground flex h-full items-center justify-center gap-2 text-sm">
      <Loader2 className="size-4 animate-spin" /> Chargement de la carte…
    </div>
  ),
});

export function Explorer() {
  const [grid, setGrid] = useState<PriceGrid | null>(null);
  const [gridError, setGridError] = useState<string | null>(null);
  const [selection, setSelection] = useState<MapSelection | null>(null);
  const [data, setData] = useState<EstimateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const [showSurface, setShowSurface] = useState(true);
  const [show3d, setShow3d] = useState(false);
  const inflight = useRef<AbortController | null>(null);

  useEffect(() => {
    const ctrl = new AbortController();
    fetchPriceGrid(ctrl.signal)
      .then(setGrid)
      .catch((e: Error) => {
        if (e.name !== "AbortError") setGridError(e.message);
      });
    return () => ctrl.abort();
  }, []);

  const onSelect = useCallback((sel: MapSelection) => {
    inflight.current?.abort();
    const ctrl = new AbortController();
    inflight.current = ctrl;
    setSelection(sel);
    setOpen(true);
    setLoading(true);
    setError(null);
    fetchEstimate(sel, ctrl.signal)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((e: Error) => {
        if (e.name === "AbortError") return;
        setError(e.message);
        setData(null);
        setLoading(false);
      });
  }, []);

  return (
    <main className="relative h-dvh w-full overflow-hidden">
      <div className="absolute inset-0">
        <PriceMap grid={grid} selection={selection} onSelect={onSelect} showSurface={showSurface} show3d={show3d} />
      </div>

      <div className="pointer-events-none absolute top-4 left-4 z-10 flex flex-col gap-3">
        <div className="bg-background/85 pointer-events-auto rounded-lg border px-4 py-3 backdrop-blur">
          <h1 className="text-sm font-semibold">Immo Quant · Paris</h1>
          <p className="text-muted-foreground text-xs">Cliquez sur une rue pour l&apos;analyse et les projections.</p>
          <div className="mt-2.5 flex gap-2">
            <Button
              size="sm"
              variant={showSurface ? "secondary" : "outline"}
              aria-pressed={showSurface}
              onClick={() => setShowSurface((v) => !v)}
            >
              <Layers /> Surface
            </Button>
            <Button size="sm" variant={show3d ? "secondary" : "outline"} aria-pressed={show3d} onClick={() => setShow3d((v) => !v)}>
              <Box /> 3D
            </Button>
          </div>
        </div>
        {gridError && (
          <div className="bg-background/85 pointer-events-auto max-w-64 rounded-lg border border-[#d03b3b]/50 px-3 py-2 text-xs backdrop-blur">
            Backend injoignable ({gridError}). Lancez l&apos;API FastAPI sur le port 8000.
          </div>
        )}
      </div>

      <div className={cn("absolute bottom-8 left-4 z-10 transition-opacity", open && "max-md:opacity-0")}>
        <PriceLegend />
      </div>

      <AnalysisSidebar open={open} data={data} loading={loading} error={error} onClose={() => setOpen(false)} />
    </main>
  );
}
