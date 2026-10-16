"use client";

import { formatEurM2 } from "@/lib/format";

export interface TooltipRow {
  key: string;
  label: string;
  value: string;
  color?: string;
  dashed?: boolean;
}

/** Shared tooltip body: value first (strong), series name second, keyed by a short line. */
export function TooltipCard({ title, rows }: { title: string; rows: TooltipRow[] }) {
  return (
    <div className="bg-popover min-w-44 rounded-md border px-3 py-2 text-xs shadow-lg">
      <div className="text-muted-foreground mb-1.5">{title}</div>
      <div className="flex flex-col gap-1">
        {rows.map((r) => (
          <div key={r.key} className="flex items-center gap-2">
            {r.color ? (
              <span
                className="inline-block w-3 border-t-2"
                style={{ borderColor: r.color, borderStyle: r.dashed ? "dashed" : "solid" }}
              />
            ) : (
              <span className="inline-block w-3" />
            )}
            <span className="text-foreground font-semibold tabular-nums">{r.value}</span>
            <span className="text-muted-foreground">{r.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export const eurRow = (key: string, label: string, value: number, color?: string): TooltipRow => ({
  key,
  label,
  value: formatEurM2(value),
  color,
});
