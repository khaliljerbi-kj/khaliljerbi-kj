import type { EstimateResponse, ScenarioKey } from "@/lib/api";
import { formatEur, formatPct, formatPctPlain } from "@/lib/format";
import { SCENARIO_STYLE } from "./projection-chart";

const ORDER: ScenarioKey[] = ["pessimistic", "median", "optimistic"];

/** Table view of the projections: every charted value is reachable without hovering. */
export function HorizonTable({ horizons }: { horizons: EstimateResponse["horizons"] }) {
  return (
    <table className="w-full text-xs tabular-nums">
      <thead>
        <tr className="text-muted-foreground border-b text-left">
          <th className="py-1.5 font-medium">Horizon</th>
          {ORDER.map((k) => (
            <th key={k} className="py-1.5 text-right font-medium">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block w-2.5 border-t-2" style={{ borderColor: SCENARIO_STYLE[k].color }} />
                {SCENARIO_STYLE[k].label}
              </span>
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {horizons.map((h) => (
          <tr key={h.years} className="border-b last:border-0">
            <td className="py-2 font-medium">
              {h.years} an{h.years > 1 ? "s" : ""}
              <div className="text-muted-foreground font-normal">P(perte) {formatPctPlain(h.prob_loss)}</div>
            </td>
            {ORDER.map((k) => (
              <td key={k} className="py-2 text-right">
                <div className="font-medium">{formatEur(h[k])}</div>
                <div className="text-muted-foreground">{formatPct(h[`${k}_cagr`])}/an</div>
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
