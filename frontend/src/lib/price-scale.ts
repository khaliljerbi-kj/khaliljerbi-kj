import type { ExpressionSpecification } from "maplibre-gl";
import type { PriceGrid } from "./api";

export const PRICE_MIN = 7000;
export const PRICE_MAX = 15000;

// Sequential single-hue ramp (blue), dark -> light so higher prices glow on the dark basemap.
export const PRICE_STOPS: [number, string][] = [
  [7000, "#184f95"],
  [9000, "#2a78d6"],
  [11000, "#5598e7"],
  [13000, "#9ec5f4"],
  [15000, "#e6f0fd"],
];

/** MapLibre `interpolate` expression mapping the `price` property to the ramp. */
export const priceColorExpression = [
  "interpolate",
  ["linear"],
  ["get", "price"],
  ...PRICE_STOPS.flat(),
] as unknown as ExpressionSpecification;

/** Bilinear sample of the backend price grid; null outside its bounds. */
export function samplePrice(grid: PriceGrid, lat: number, lon: number): number | null {
  const fy = ((lat - grid.lat_min) / (grid.lat_max - grid.lat_min)) * (grid.n_lat - 1);
  const fx = ((lon - grid.lon_min) / (grid.lon_max - grid.lon_min)) * (grid.n_lon - 1);
  if (fy < 0 || fx < 0 || fy > grid.n_lat - 1 || fx > grid.n_lon - 1) return null;
  const y0 = Math.floor(fy);
  const x0 = Math.floor(fx);
  const y1 = Math.min(y0 + 1, grid.n_lat - 1);
  const x1 = Math.min(x0 + 1, grid.n_lon - 1);
  const ty = fy - y0;
  const tx = fx - x0;
  const v = (y: number, x: number) => grid.values[y * grid.n_lon + x];
  const top = v(y1, x0) * (1 - tx) + v(y1, x1) * tx;
  const bottom = v(y0, x0) * (1 - tx) + v(y0, x1) * tx;
  return bottom * (1 - ty) + top * ty;
}

/** Grid cells as polygons, for the translucent price surface under the streets. */
export function gridToCells(grid: PriceGrid): GeoJSON.FeatureCollection<GeoJSON.Polygon, { price: number }> {
  const dLat = (grid.lat_max - grid.lat_min) / (grid.n_lat - 1);
  const dLon = (grid.lon_max - grid.lon_min) / (grid.n_lon - 1);
  const features: GeoJSON.Feature<GeoJSON.Polygon, { price: number }>[] = [];
  for (let y = 0; y < grid.n_lat; y++) {
    for (let x = 0; x < grid.n_lon; x++) {
      const lat = grid.lat_min + y * dLat;
      const lon = grid.lon_min + x * dLon;
      const [s, n, w, e] = [lat - dLat / 2, lat + dLat / 2, lon - dLon / 2, lon + dLon / 2];
      features.push({
        type: "Feature",
        properties: { price: grid.values[y * grid.n_lon + x] },
        geometry: { type: "Polygon", coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] },
      });
    }
  }
  return { type: "FeatureCollection", features };
}
