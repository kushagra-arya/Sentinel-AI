"use client";

import { useQuery } from "@tanstack/react-query";
import { Layers, Upload } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { apiPost } from "@/lib/api";
import { getDemoStatus } from "@/lib/demo";
import { canMutate, canSeeArea, type AccessContext } from "@/lib/rbac";

type Coordinate = { x: number; y: number };
type MapMarker = {
  id: string;
  marker_type: string;
  title: string;
  zone: string | null;
  coordinate: Coordinate | null;
  status: string;
  evidence_link: string | null;
};
type HeatmapCell = {
  x: number;
  y: number;
  intensity: number;
  contributing_alert_ids: string[];
};
type ViewportResponse = {
  markers: MapMarker[];
  heatmap: HeatmapCell[];
};

const plantId = "demo-plant";
const allLayers = ["sensors", "workers", "equipment", "permits", "hazards", "alerts", "heatmap"];

const fallbackMarkers: MapMarker[] = [
  {
    id: "gas-01",
    marker_type: "sensor",
    title: "Gas Sensor 01",
    zone: "Zone A",
    coordinate: { x: 24, y: 46 },
    status: "active",
    evidence_link: "/api/v1/sensors/gas-01"
  },
  {
    id: "worker-17",
    marker_type: "worker",
    title: "Worker 17",
    zone: "Zone A",
    coordinate: { x: 32, y: 52 },
    status: "present",
    evidence_link: "/api/v1/worker-location-events/worker-17"
  },
  {
    id: "alert-09",
    marker_type: "alert",
    title: "High compound gas risk",
    zone: "Zone A",
    coordinate: { x: 28, y: 48 },
    status: "high",
    evidence_link: "/api/v1/timeline/alerts/alert-09"
  }
];

const fallbackHeatmap: HeatmapCell[] = [
  { x: 28, y: 48, intensity: 0.88, contributing_alert_ids: ["alert-09"] },
  { x: 36, y: 52, intensity: 0.55, contributing_alert_ids: ["alert-09"] },
  { x: 18, y: 40, intensity: 0.34, contributing_alert_ids: ["alert-09"] }
];

export function PlantMapClient({ access }: Readonly<{ access: AccessContext }>) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletMap = useRef<import("leaflet").Map | null>(null);
  const markerLayer = useRef<import("leaflet").LayerGroup | null>(null);
  const heatLayer = useRef<import("leaflet").LayerGroup | null>(null);
  const [leaflet, setLeaflet] = useState<typeof import("leaflet") | null>(null);
  const [layers, setLayers] = useState(allLayers);
  const [layoutName, setLayoutName] = useState("Refinery Unit A");
  const demoQuery = useQuery({
    queryKey: ["demo-status"],
    queryFn: getDemoStatus,
    refetchInterval: 2_000,
    staleTime: 1_000
  });
  const activePlantId = demoQuery.data?.plant_id ?? plantId;

  const viewportPayload = useMemo(
    () => ({
      plant_id: activePlantId,
      zoom: 1,
      min_x: 0,
      min_y: 0,
      max_x: 100,
      max_y: 100,
      layers
    }),
    [activePlantId, layers]
  );

  const { data } = useQuery({
    queryKey: ["map-viewport", viewportPayload],
    queryFn: () => apiPost<ViewportResponse, typeof viewportPayload>("/map/viewport", viewportPayload),
    refetchInterval: 15_000
  });

  const markers = (data?.markers ?? fallbackMarkers).filter((marker) => canSeeArea(access, marker.zone));
  const heatmap = data?.heatmap?.length ? data.heatmap : fallbackHeatmap;

  useEffect(() => {
    if (!mapRef.current || leafletMap.current) {
      return;
    }
    void import("leaflet").then((leafletModule) => {
      if (!mapRef.current || leafletMap.current) {
        return;
      }
      const map = leafletModule.map(mapRef.current, {
        crs: leafletModule.CRS.Simple,
        minZoom: -1,
        maxZoom: 3,
        zoomControl: true,
        attributionControl: false
      });
      const bounds: import("leaflet").LatLngBoundsExpression = [
        [0, 0],
        [100, 100]
      ];
      leafletModule
        .rectangle(bounds, { color: "#334155", weight: 1, fillColor: "#020617", fillOpacity: 1 })
        .addTo(map);
      map.fitBounds(bounds);
      leafletMap.current = map;
      markerLayer.current = leafletModule.layerGroup().addTo(map);
      heatLayer.current = leafletModule.layerGroup().addTo(map);
      setLeaflet(leafletModule);
    });
  }, []);

  useEffect(() => {
    if (!leaflet || !leafletMap.current || !markerLayer.current || !heatLayer.current) {
      return;
    }
    markerLayer.current.clearLayers();
    heatLayer.current.clearLayers();

    if (layers.includes("heatmap")) {
      heatmap.forEach((cell) => {
        leaflet.circle([cell.y, cell.x], {
          radius: 7 + cell.intensity * 12,
          color: "transparent",
          fillColor: cell.intensity > 0.75 ? "#ef4444" : cell.intensity > 0.45 ? "#f59e0b" : "#22c55e",
          fillOpacity: 0.24 + cell.intensity * 0.28
        }).addTo(heatLayer.current as import("leaflet").LayerGroup);
      });
    }

    markers.forEach((marker) => {
      if (!marker.coordinate || !layers.includes(layerNameForMarker(marker.marker_type))) {
        if (marker.marker_type !== "alert" || !layers.includes("alerts")) {
          return;
        }
      }
      if (!marker.coordinate) {
        return;
      }
      const color = marker.status === "critical" ? "#ef4444" : marker.status === "high" ? "#f59e0b" : "#38bdf8";
      const leafletMarker = leaflet.circleMarker([marker.coordinate.y, marker.coordinate.x], {
        radius: marker.marker_type === "alert" ? 8 : 6,
        color,
        fillColor: color,
        fillOpacity: marker.marker_type === "alert" ? 0.9 : 0.65,
        weight: 1
      }).bindPopup(`<strong>${marker.title}</strong><br/>${marker.marker_type} | ${marker.zone ?? "No zone"}`);
      leafletMarker.addTo(markerLayer.current as import("leaflet").LayerGroup);
    });
  }, [heatmap, layers, leaflet, markers]);

  return (
    <div className="grid gap-4 xl:grid-cols-[1fr_320px]">
      <section className="min-h-[680px] overflow-hidden rounded-md border border-border bg-card">
        <div className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="text-base font-semibold">{layoutName}</h2>
            <p className="text-sm text-muted-foreground">Zoom and pan enabled | CRS plant coordinates</p>
          </div>
          <Button variant="outline" disabled={!canMutate(access)}>
            <Upload className="mr-2 h-4 w-4" />
            Upload Layout
          </Button>
        </div>
        <div ref={mapRef} className="h-[620px] w-full bg-background" />
      </section>

      <aside className="flex flex-col gap-4">
        <section className="rounded-md border border-border bg-card p-4">
          <div className="flex items-center gap-2">
            <Layers className="h-4 w-4 text-informational" />
            <h2 className="text-sm font-semibold">Layers</h2>
          </div>
          <div className="mt-4 grid gap-3">
            {allLayers.map((layer) => (
              <label key={layer} className="flex items-center justify-between text-sm">
                <span className="capitalize text-muted-foreground">{layer}</span>
                <input
                  type="checkbox"
                  checked={layers.includes(layer)}
                  onChange={(event) => {
                    setLayers((current) =>
                      event.target.checked
                        ? [...current, layer]
                        : current.filter((item) => item !== layer)
                    );
                  }}
                  className="h-4 w-4 accent-sky-500"
                />
              </label>
            ))}
          </div>
        </section>

        <section className="rounded-md border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Layout Metadata</h2>
          <label className="mt-4 block text-sm text-muted-foreground">
            Layout name
            <input
              value={layoutName}
              onChange={(event) => setLayoutName(event.target.value)}
              disabled={!canMutate(access)}
              className="mt-2 h-10 w-full rounded-md border border-border bg-background px-3 text-foreground"
            />
          </label>
        </section>

        <section className="rounded-md border border-border bg-card p-4">
          <h2 className="text-sm font-semibold">Visible Evidence</h2>
          <div className="mt-3 space-y-3">
            {markers.map((marker) => (
              <a
                key={marker.id}
                href={marker.evidence_link ?? "#"}
                className="block rounded-md border border-border px-3 py-2 text-sm hover:bg-background"
              >
                <span className="block text-foreground">{marker.title}</span>
                <span className="text-muted-foreground">{marker.marker_type} | {marker.zone ?? "No zone"}</span>
              </a>
            ))}
          </div>
        </section>
      </aside>
    </div>
  );
}

function layerNameForMarker(markerType: string) {
  return {
    sensor: "sensors",
    worker: "workers",
    equipment: "equipment",
    permit: "permits",
    hazard: "hazards",
    alert: "alerts"
  }[markerType] ?? markerType;
}
