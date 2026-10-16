"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import type { EstimateResponse } from "@/lib/api";
import { formatK } from "@/lib/format";
import { TooltipCard, eurRow } from "./chart-tooltip";

const AXIS = { stroke: "var(--chart-axis)", tick: { fill: "var(--chart-muted)", fontSize: 11 } };

export function HistoryChart({ data }: { data: EstimateResponse["history"] }) {
  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 24, bottom: 0, left: 0 }}>
        <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
        <XAxis dataKey="label" {...AXIS} tickLine={false} interval={3} />
        <YAxis {...AXIS} tickLine={false} axisLine={false} width={56} domain={["auto", "auto"]} tickFormatter={formatK} />
        <Tooltip
          cursor={{ stroke: "var(--chart-muted)", strokeWidth: 1 }}
          content={({ active, payload, label }) =>
            active && payload?.length ? (
              <TooltipCard
                title={String(label)}
                rows={[eurRow("price", "Prix moyen", Number(payload[0].value), "var(--series-history)")]}
              />
            ) : null
          }
        />
        <Line
          type="monotone"
          dataKey="price"
          stroke="var(--series-history)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, stroke: "var(--chart-surface)", strokeWidth: 2 }}
          isAnimationActive={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
