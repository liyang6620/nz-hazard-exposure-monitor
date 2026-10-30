import { AlertTriangle, Layers3 } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import "@arcgis/core/assets/esri/themes/light/main.css";

import type { EventSummary } from "../data/types";
import type Layer from "@arcgis/core/layers/Layer.js";
import type MapView from "@arcgis/core/views/MapView.js";

interface EventMapProps {
  event: EventSummary;
  exposureUrl: string;
}

export default function EventMap({ event, exposureUrl }: EventMapProps) {
  const mapElement = useRef<HTMLDivElement>(null);
  const [mapError, setMapError] = useState<string | null>(null);
  const [provider, setProvider] = useState<"LINZ" | "OpenStreetMap">(
    "OpenStreetMap",
  );

  useEffect(() => {
    if (!mapElement.current) return;
    let view: MapView | undefined;
    let cancelled = false;

    async function createMap() {
      const [
        { default: ArcGISMap },
        { default: MapView },
        { default: GeoJSONLayer },
        { default: WebTileLayer },
        { default: VectorTileLayer },
        { default: Basemap },
        { default: GraphicsLayer },
        { default: Graphic },
      ] = await Promise.all([
        import("@arcgis/core/Map.js"),
        import("@arcgis/core/views/MapView.js"),
        import("@arcgis/core/layers/GeoJSONLayer.js"),
        import("@arcgis/core/layers/WebTileLayer.js"),
        import("@arcgis/core/layers/VectorTileLayer.js"),
        import("@arcgis/core/Basemap.js"),
        import("@arcgis/core/layers/GraphicsLayer.js"),
        import("@arcgis/core/Graphic.js"),
      ]);
      if (cancelled || !mapElement.current) return;

      const linzKey = import.meta.env.VITE_LINZ_BASEMAPS_API_KEY?.trim();
      let baseLayer: Layer;
      if (linzKey) {
        const linzLayer = new VectorTileLayer({
          url: `https://basemaps.linz.govt.nz/v1/tiles/topographic/WebMercatorQuad/style/topographic.json?api=${encodeURIComponent(linzKey)}`,
          title: "LINZ Topographic",
        });
        try {
          await linzLayer.load();
          baseLayer = linzLayer;
          setProvider("LINZ");
        } catch {
          baseLayer = osmLayer(WebTileLayer);
        }
      } else {
        baseLayer = osmLayer(WebTileLayer);
      }

      const exposure = new GeoJSONLayer({
        url: exposureUrl,
        title: "Earthquake exposure",
        outFields: ["*"],
        renderer: {
          type: "class-breaks",
          field: "mmi",
          classBreakInfos: [
            mapClass(5, 5.99, "#fff200", "MMI 5"),
            mapClass(6, 6.99, "#ffb300", "MMI 6"),
            mapClass(7, 7.99, "#ff6800", "MMI 7"),
            mapClass(8, 20, "#d7191c", "MMI 8+"),
          ],
        },
        popupTemplate: {
          title: "Exposure cell · MMI {mmi}",
          content: [
            {
              type: "fields",
              fieldInfos: [
                {
                  fieldName: "mmi",
                  label: "Modified Mercalli Intensity",
                  format: { places: 1 },
                },
                {
                  fieldName: "buildings",
                  label: "Buildings",
                  format: { digitSeparator: true, places: 0 },
                },
                {
                  fieldName: "population",
                  label: "Population",
                  format: { digitSeparator: true, places: 0 },
                },
              ],
            },
          ],
        },
      });
      const epicentre = new GraphicsLayer({ title: "Earthquake epicentre" });
      epicentre.add(
        new Graphic({
          geometry: {
            type: "point",
            longitude: event.longitude,
            latitude: event.latitude,
          },
          symbol: {
            type: "simple-marker",
            style: "diamond",
            size: 16,
            color: "#171815",
            outline: { color: "#f2eddf", width: 2 },
          },
          popupTemplate: {
            title: `${event.name} epicentre`,
            content: `M${event.magnitude.toFixed(1)} · ${event.depth_km.toFixed(1)} km depth`,
          },
        }),
      );

      const map = new ArcGISMap({
        basemap: new Basemap({ baseLayers: [baseLayer] }),
        layers: [exposure, epicentre],
      });
      view = new MapView({
        container: mapElement.current,
        map,
        center: [event.longitude, event.latitude],
        zoom: event.no_damaging_shaking ? 6 : 7,
        constraints: { minZoom: 3, maxZoom: 13 },
      });
      await view.when();
      await exposure.load();
      if (exposure.fullExtent && exposure.fullExtent.width > 0) {
        await view.goTo(exposure.fullExtent.expand(1.25), { animate: false });
      }
    }

    createMap().catch((reason: unknown) => {
      if (!cancelled)
        setMapError(
          reason instanceof Error
            ? reason.message
            : "The map could not be displayed",
        );
    });
    return () => {
      cancelled = true;
      view?.destroy();
    };
  }, [event, exposureUrl]);

  return (
    <div className="map-frame">
      <div className="map-heading">
        <div>
          <Layers3 size={18} aria-hidden="true" />
          <strong>Shaking and H3 exposure</strong>
        </div>
        <span>{provider} basemap</span>
      </div>
      {mapError ? (
        <div className="map-error" role="alert">
          <AlertTriangle size={20} />
          <span>Interactive map unavailable. {mapError}</span>
        </div>
      ) : (
        <div
          className="map-canvas"
          ref={mapElement}
          role="region"
          aria-label={`Interactive shaking and exposure map for ${event.name}`}
          data-testid="event-map"
        />
      )}
      <div className="map-footer">
        <span>H3 resolution 6 exposure cells</span>
        <span>
          {provider === "LINZ"
            ? "Basemap © Toitū Te Whenua LINZ, CC BY 4.0"
            : "Basemap © OpenStreetMap contributors"}
        </span>
      </div>
    </div>
  );
}

function osmLayer(
  WebTileLayer: typeof import("@arcgis/core/layers/WebTileLayer.js").default,
) {
  return new WebTileLayer({
    urlTemplate: "https://tile.openstreetmap.org/{level}/{col}/{row}.png",
    title: "OpenStreetMap",
    copyright: "© OpenStreetMap contributors",
  });
}

function mapClass(
  minValue: number,
  maxValue: number,
  colour: string,
  label: string,
) {
  return {
    minValue,
    maxValue,
    label,
    symbol: {
      type: "simple-fill" as const,
      color: `${colour}cc`,
      outline: { color: "#ffffff80", width: 0.35 },
    },
  };
}
