// Types mirror backend/app/schemas.py. Requests go to /api/* which Next.js
// rewrites to the FastAPI server (see next.config.ts).

export type ScenarioKey = "pessimistic" | "median" | "optimistic";

export interface EstimateResponse {
  location: { lat: number; lon: number; street: string | null; arrondissement: number; label: string };
  current_price_m2: number;
  currency: string;
  history: { date: string; label: string; price: number }[];
  projection: ({ t: number; label: string; p5: number; p25: number; p75: number; p95: number } & Record<
    ScenarioKey,
    number
  >)[];
  horizons: ({
    years: number;
    prob_loss: number;
    var95: number;
  } & Record<ScenarioKey, number> &
    Record<`${ScenarioKey}_cagr`, number>)[];
  scenarios: { key: ScenarioKey; label: string; description: string; mu: number; sigma: number }[];
  calibration: { hist_mu: number; hist_sigma: number; n_paths: number; steps_per_year: number; seed: number };
  is_mock: boolean;
}

export interface PriceGrid {
  lat_min: number;
  lat_max: number;
  lon_min: number;
  lon_max: number;
  n_lat: number;
  n_lon: number;
  values: number[];
  min: number;
  max: number;
}

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ? String(body.detail) : `Erreur API (${res.status})`);
  }
  return res.json() as Promise<T>;
}

export function fetchEstimate(
  query: { lat: number; lon: number; street?: string | null },
  signal?: AbortSignal,
): Promise<EstimateResponse> {
  const params = new URLSearchParams({ lat: query.lat.toFixed(6), lon: query.lon.toFixed(6) });
  if (query.street) params.set("street", query.street);
  return getJson(`/api/estimate?${params}`, signal);
}

export function fetchPriceGrid(signal?: AbortSignal): Promise<PriceGrid> {
  return getJson("/api/price-grid", signal);
}
