import { PRICE_STOPS } from "@/lib/price-scale";

export function PriceLegend() {
  const gradient = `linear-gradient(to right, ${PRICE_STOPS.map(([, c]) => c).join(", ")})`;
  return (
    <div className="bg-background/85 w-56 rounded-lg border p-3 backdrop-blur">
      <div className="mb-2 text-xs font-medium">Prix estimé au m²</div>
      <div className="h-2 rounded-full" style={{ background: gradient }} />
      <div className="text-muted-foreground mt-1 flex justify-between text-[11px] tabular-nums">
        <span>7 k€</span>
        <span>11 k€</span>
        <span>15 k€</span>
      </div>
    </div>
  );
}
