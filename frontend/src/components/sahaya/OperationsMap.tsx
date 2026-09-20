"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import { LngLatBoundsLike, Map } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { EvaluationStatus } from "@/lib/api";

export interface OperationMapMarker {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  status: EvaluationStatus;
}

const markerColors: Record<EvaluationStatus, string> = {
  SAFE: "#15803d",
  UNKNOWN: "#d97706",
  BLOCKED: "#dc2626",
  NOT_APPLICABLE: "#6b7280",
};

export function OperationsMap({
  incident,
  resources,
  onSelect,
}: {
  incident?: { latitude: number; longitude: number; label: string };
  resources: OperationMapMarker[];
  onSelect: (resourceId: string) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<Map | null>(null);

  useEffect(() => {
    if (!container.current || map.current) return;
    const points = [
      ...(incident ? [[incident.longitude, incident.latitude] as [number, number]] : []),
      ...resources.map((resource) => [resource.longitude, resource.latitude] as [number, number]),
    ];
    const center = points[0] ?? [75.7804, 11.2588] as [number, number];
    const instance = new maplibregl.Map({
      container: container.current,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            tileSize: 256,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
      center,
      zoom: 12,
    });
    map.current = instance;
    instance.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

    if (incident) {
      const element = document.createElement("button");
      element.className = "operation-marker operation-marker-incident";
      element.setAttribute("aria-label", "Incident: " + incident.label);
      element.textContent = "!";
      new maplibregl.Marker({ element })
        .setLngLat([incident.longitude, incident.latitude])
        .setPopup(new maplibregl.Popup({ offset: 18 }).setText("INCIDENT · " + incident.label))
        .addTo(instance);
    }
    resources.forEach((resource) => {
      const element = document.createElement("button");
      element.className = "operation-marker";
      element.style.backgroundColor = markerColors[resource.status];
      element.setAttribute("aria-label", resource.name + ": " + resource.status);
      element.addEventListener("click", () => onSelect(resource.id));
      new maplibregl.Marker({ element })
        .setLngLat([resource.longitude, resource.latitude])
        .setPopup(new maplibregl.Popup({ offset: 18 }).setText(resource.name + " · " + resource.status))
        .addTo(instance);
    });
    if (points.length > 1) {
      instance.fitBounds(points as LngLatBoundsLike, { padding: 56, maxZoom: 13, duration: 0 });
    }
    return () => {
      instance.remove();
      map.current = null;
    };
  }, [incident, resources, onSelect]);

  return <div ref={container} className="h-[480px] overflow-hidden rounded-2xl border border-gray-200 shadow-sm" />;
}
