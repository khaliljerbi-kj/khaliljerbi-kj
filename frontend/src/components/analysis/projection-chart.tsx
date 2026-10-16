"use client";

import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { EstimateResponse, ScenarioKey } from "@/lib/api";
import { formatK } from "@/lib/format";
import { TooltipCard, eurRow } from "./chart-tooltip";

export const SCENARIO_STYLE: Record<ScenarioKey, { color: string; label: string }> = {
  optimistic: { color: "var(--series-optimistic)", label: "Optimiste" },
  median: { color: "var(--series-median)", label: "Médian" },
  pessimistic: { color: "var(--series-pessimistic)", label: "Pessimiste" },
};
const ORDER: ScenarioKey[] = ["optimistic", "median", "pessimistic"];
const AXIS = { stroke: "var(--chart-axis)", tick: { fill: "var(--chart-muted)", fontSize: 11 } };

export function ProjectionChart({ data }: { data: EstimateResponse["projection"] }) {
  const rows = data.map((d) => ({ ...d, band90: [d.p5, d.p95], band50: [d.p25, d.p75] }));
  const last = rows.length - 1;

  return (
    <div>
      <ul className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs" aria-label="Légende">
        {ORDER.map((k) => (
          <li key={k} className="text-muted-foreground flex items-center gap-1.5">
            <span className="inline-block w-4 border-t-2" style={{ borderColor: SCENARIO_STYLE[k].color }} />
            {SCENARIO_STYLE[k].label}
          </li>
        ))}
        <li className="text-muted-foreground flex items-center gap-1.5">
          <span className="inline-block h-2.5 w-4 rounded-sm bg-[var(--series-median)]/25" />
          Intervalle 50 % / 90 %
        </li>
      </ul>
      <ResponsiveContainer width="100%" height={240}>
        <ComposedChart data={rows} margin={{ top: 8, right: 64, bottom: 0, left: 0 }}>
          <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            domain={[0, 10]}
            ticks={[0, 1, 5, 10]}
            tickFormatter={(t: number) => (t === 0 ? "Auj." : `+${t} an${t > 1 ? "s" : ""}`)}
            {...AXIS}
            tickLine={false}
          />
          <YAxis {...AXIS} tickLine={false} axisLine={false} width={56} domain={["auto", "auto"]} tickFormatter={formatK} />
          {[1, 5, 10].map((h) => (
            <ReferenceLine key={h} x={h} stroke="var(--chart-axis)" strokeDasharray="3 3" />
          ))}
          <Tooltip
            cursor={{ stroke: "var(--chart-muted)", strokeWidth: 1 }}
            content={({ active, payload }) => {
              const p = payload?.[0]?.payload as (typeof rows)[number] | undefined;
              if (!active || !p) return null;
              return (
                <TooltipCard
                  title={p.label}
                  rows={[
                    ...ORDER.map((k) => eurRow(k, SCENARIO_STYLE[k].label, p[k], SCENARIO_STYLE[k].color)),
                    eurRow("p95", "P95 (médian)", p.p95),
                    eurRow("p5", "P5 (médian)", p.p5),
                  ]}
                />
              );
            }}
          />
          <Area dataKey="band90" stroke="none" fill="var(--series-median)" fillOpacity={0.12} isAnimationActive={false} activeDot={false} />
          <Area dataKey="band50" stroke="none" fill="var(--series-median)" fillOpacity={0.22} isAnimationActive={false} activeDot={false} />
          {ORDER.map((k) => (
            <Line
              key={k}
              type="monotone"
              dataKey={k}
              stroke={SCENARIO_STYLE[k].color}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4, stroke: "var(--chart-surface)", strokeWidth: 2 }}
              isAnimationActive={false}
              label={(props: { index?: number; x?: number | string; y?: number | string }) =>
                props.index === last ? (
                  <text key={k} x={Number(props.x) + 6} y={Number(props.y)} dy={4} fontSize={11} fill="var(--foreground)">
                    {SCENARIO_STYLE[k].label}
                  </text>
                ) : (
                  <g key={`${k}-${props.index}`} />
                )
              }
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
