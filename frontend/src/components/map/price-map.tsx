"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Layer,
  Map,
  Marker,
  NavigationControl,
  Popup,
  ScaleControl,
  Source,
  type MapLayerMouseEvent,
  type MapRef,
} from "react-map-gl/maplibre";
import type { MapGeoJSONFeature, Map as MaplibreMap, MapSourceDataEvent } from "maplibre-gl";

import type { PriceGrid } from "@/lib/api";
import { formatEurM2 } from "@/lib/format";
import { gridToCells, priceColorExpression, samplePrice } from "@/lib/price-scale";

// Free vector basemap (OpenMapTiles schema) — no access token required.
const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";
export const PARIS_CENTER = { latitude: 48.8566, longitude: 2.3522 };

const STREET_LAYER = "street-prices";
const STREET_CLASSES = new Set(["motorway", "trunk", "primary", "secondary", "tertiary", "minor", "street", "residential", "service"]);

type StreetProps = { name: string; price: number; class: string };
type StreetCollection = GeoJSON.FeatureCollection<GeoJSON.LineString | GeoJSON.MultiLineString, StreetProps>;

export interface MapSelection {
  lat: number;
  lon: number;
  street: string | null;
}

interface PriceMapProps {
  grid: PriceGrid | null;
  selection: MapSelection | null;
  onSelect: (selection: MapSelection) => void;
  showSurface: boolean;
  show3d: boolean;
}

function midpoint(geometry: GeoJSON.Geometry): [number, number] | null {
  const line =
    geometry.type === "LineString" ? geometry.coordinates : geometry.type === "MultiLineString" ? geometry.coordinates[0] : null;
  if (!line || line.length === 0) return null;
  const [lon, lat] = line[Math.floor(line.length / 2)];
  return [lon, lat];
}

/** Find the vector source carrying the OpenMapTiles layers, whatever the style calls it. */
function findVectorSource(map: MaplibreMap): string | null {
  const sources = map.getStyle()?.sources ?? {};
  return Object.keys(sources).find((id) => sources[id].type === "vector") ?? null;
}

function firstSymbolLayer(map: MaplibreMap): string | undefined {
  return map.getStyle()?.layers?.find((l) => l.type === "symbol")?.id;
}

export default function PriceMap({ grid, selection, onSelect, showSurface, show3d }: PriceMapProps) {
  const mapRef = useRef<MapRef>(null);
  const [streets, setStreets] = useState<StreetCollection>({ type: "FeatureCollection", features: [] });
  const [vectorSource, setVectorSource] = useState<string | null>(null);
  const [beforeId, setBeforeId] = useState<string | undefined>(undefined);
  const [hover, setHover] = useState<{ lon: number; lat: number; name: string; price: number } | null>(null);
  const signature = useRef("");
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cells = useMemo(() => (grid ? gridToCells(grid) : null), [grid]);

  // Re-colour the streets present in the loaded tiles with the price surface.
  const refreshStreets = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map || !grid || !vectorSource) return;
    const raw = map.querySourceFeatures(vectorSource, { sourceLayer: "transportation_name" });
    const bounds = map.getBounds();
    const sig = `${raw.length}|${bounds.toArray().flat().map((v) => v.toFixed(3)).join(",")}`;
    if (sig === signature.current) return;
    signature.current = sig;

    const features: StreetCollection["features"] = [];
    for (const f of raw) {
      const name = (f.properties?.name ?? f.properties?.["name:latin"]) as string | undefined;
      const cls = String(f.properties?.class ?? "minor");
      if (!name || !STREET_CLASSES.has(cls)) continue;
      if (f.geometry.type !== "LineString" && f.geometry.type !== "MultiLineString") continue;
      const mid = midpoint(f.geometry);
      const price = mid && samplePrice(grid, mid[1], mid[0]);
      if (!price) continue;
      features.push({ type: "Feature", geometry: f.geometry, properties: { name, price: Math.round(price), class: cls } });
    }
    setStreets({ type: "FeatureCollection", features });
  }, [grid, vectorSource]);

  const scheduleRefresh = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(refreshStreets, 120);
  }, [refreshStreets]);

  useEffect(() => {
    signature.current = ""; // Grid or source changed: force a recompute.
    scheduleRefresh();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [scheduleRefresh]);

  const onLoad = useCallback(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    setVectorSource(findVectorSource(map));
    setBeforeId(firstSymbolLayer(map));
  }, []);

  const onSourceData = useCallback(
    (e: MapSourceDataEvent) => {
      if (e.sourceId === vectorSource && e.isSourceLoaded) scheduleRefresh();
    },
    [vectorSource, scheduleRefresh],
  );

  const pickStreet = (e: MapLayerMouseEvent): MapGeoJSONFeature | undefined => {
    const direct = e.features?.find((f) => f.layer.id === STREET_LAYER);
    if (direct) return direct;
    // Clicked a building or a block: take the closest street within a few pixels.
    const map = mapRef.current?.getMap();
    if (!map || !map.getLayer(STREET_LAYER)) return undefined;
    const { x, y } = e.point;
    const r = 14;
    return map.queryRenderedFeatures(
      [
        [x - r, y - r],
        [x + r, y + r],
      ],
      { layers: [STREET_LAYER] },
    )[0];
  };

  const onClick = (e: MapLayerMouseEvent) => {
    const street = pickStreet(e);
    onSelect({ lat: e.lngLat.lat, lon: e.lngLat.lng, street: (street?.properties?.name as string) ?? null });
  };

  const onMouseMove = (e: MapLayerMouseEvent) => {
    const f = e.features?.find((feat) => feat.layer.id === STREET_LAYER);
    setHover(f ? { lon: e.lngLat.lng, lat: e.lngLat.lat, name: f.properties.name, price: f.properties.price } : null);
  };

  useEffect(() => {
    const map = mapRef.current?.getMap();
    if (!map) return;
    map.easeTo({ pitch: show3d ? 55 : 0, bearing: show3d ? -17 : 0, duration: 800 });
  }, [show3d]);

  return (
    <Map
      ref={mapRef}
      initialViewState={{ ...PARIS_CENTER, zoom: 13 }}
      minZoom={10.5}
      maxZoom={18}
      maxBounds={[2.05, 48.72, 2.65, 49.0]}
      mapStyle={BASEMAP_STYLE}
      style={{ width: "100%", height: "100%" }}
      interactiveLayerIds={[STREET_LAYER]}
      cursor={hover ? "pointer" : "crosshair"}
      onLoad={onLoad}
      onSourceData={onSourceData}
      onMoveEnd={scheduleRefresh}
      onClick={onClick}
      onMouseMove={onMouseMove}
      onMouseLeave={() => setHover(null)}
      attributionControl={{ compact: true }}
    >
      <NavigationControl position="bottom-right" visualizePitch />
      <ScaleControl position="bottom-left" unit="metric" />

      {cells && (
        <Source id="price-surface" type="geojson" data={cells}>
          <Layer
            id="price-surface"
            type="fill"
            beforeId={beforeId}
            layout={{ visibility: showSurface ? "visible" : "none" }}
            paint={{
              "fill-color": priceColorExpression,
              "fill-antialias": false,
              "fill-opacity": ["interpolate", ["linear"], ["zoom"], 11, 0.4, 14, 0.18, 16, 0.06],
            }}
          />
        </Source>
      )}

      {vectorSource && show3d && (
        <Layer
          id="buildings-3d"
          type="fill-extrusion"
          source={vectorSource}
          source-layer="building"
          minzoom={13}
          beforeId={beforeId}
          paint={{
            "fill-extrusion-color": "#2c2c2a",
            "fill-extrusion-height": ["coalesce", ["get", "render_height"], 12],
            "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
            "fill-extrusion-opacity": 0.85,
          }}
        />
      )}

      <Source id="streets" type="geojson" data={streets}>
        <Layer
          id="street-selected"
          type="line"
          beforeId={beforeId}
          filter={["==", ["get", "name"], selection?.street ?? ""]}
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            "line-color": "#f0efec",
            "line-width": ["interpolate", ["linear"], ["zoom"], 11, 4, 15, 9, 18, 18],
          }}
        />
        <Layer
          id={STREET_LAYER}
          type="line"
          beforeId={beforeId}
          layout={{ "line-cap": "round", "line-join": "round" }}
          paint={{
            "line-color": priceColorExpression,
            "line-width": [
              "interpolate",
              ["linear"],
              ["zoom"],
              11,
              ["match", ["get", "class"], ["primary", "secondary", "trunk", "motorway"], 2, 1],
              15,
              ["match", ["get", "class"], ["primary", "secondary", "trunk", "motorway"], 6, 3.5],
              18,
              ["match", ["get", "class"], ["primary", "secondary", "trunk", "motorway"], 14, 9],
            ],
            "line-opacity": 0.95,
          }}
        />
      </Source>

      {hover && (
        <Popup longitude={hover.lon} latitude={hover.lat} closeButton={false} offset={12} anchor="bottom">
          <div className="text-sm font-semibold tabular-nums">{formatEurM2(hover.price)}</div>
          <div className="text-muted-foreground text-xs">{hover.name}</div>
        </Popup>
      )}

      {selection && (
        <Marker longitude={selection.lon} latitude={selection.lat} anchor="center">
          <span className="block size-4 rounded-full border-2 border-[#1a1a19] bg-[#f0efec] shadow-[0_0_0_4px_rgba(240,239,236,0.25)]" />
        </Marker>
      )}
    </Map>
  );
}
