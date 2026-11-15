import maplibregl, { type GeoJSONSource, type Map as MapLibreMap, type StyleSpecification } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { Crosshair, ImageDown } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useAtlas } from "@/context/AtlasStateContext";
import { MEXICO_VIEW, VARIABLES } from "@/config/variables";
import { gridCorners, gridToImage } from "@/components/maps/gridImage";
import { api } from "@/services/api";
import type { LayerResponse } from "@/services/types";

const BASEMAP = import.meta.env.VITE_BASEMAP_STYLE || "https://tiles.openfreemap.org/styles/positron";

/** Estilo mínimo de respaldo si el mapa base no carga (sin internet, por ejemplo). */
const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  sources: {},
  layers: [{ id: "fondo", type: "background", paint: { "background-color": "#D9E7EA" } }],
};

const DATA_SOURCE = "atlas-datos";
const DATA_LAYER = "atlas-datos-capa";

function firstLabelLayer(map: MapLibreMap): string | undefined {
  return map.getStyle().layers?.find((l) => l.type === "symbol")?.id;
}

/**
 * Mapa interactivo (MapLibre GL JS).
 *
 * - Muestra todo México al inicio; se puede acercar, alejar y desplazar
 *   (también con el teclado: flechas y +/−).
 * - La capa de datos es una imagen de malla (DEMO) o teselas de TiTiler (REALES).
 * - Límites estatales y municipales del INEGI cuando el backend los tiene.
 * - Un clic consulta el valor en ese lugar.
 */
export function AtlasMap({ layer, theme }: { layer: LayerResponse | null; theme: "claro" | "oscuro" }) {
  const { state, dispatch } = useAtlas();
  const container = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const markerRef = useRef<maplibregl.Marker | null>(null);
  // Cambia cada vez que se (re)carga el estilo: las capas propias deben volver a agregarse.
  const [styleVersion, setStyleVersion] = useState(0);
  const ready = styleVersion > 0;
  const [boundaryMessage, setBoundaryMessage] = useState<string | null>(null);

  // Crear el mapa una sola vez.
  useEffect(() => {
    if (!container.current) return;
    const map = new maplibregl.Map({
      container: container.current,
      style: BASEMAP,
      bounds: MEXICO_VIEW.bounds,
      fitBoundsOptions: { padding: 24 },
      attributionControl: { compact: true },
      canvasContextAttributes: { preserveDrawingBuffer: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    map.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
    let usedFallback = false;
    map.on("error", (event) => {
      if (!map.isStyleLoaded() && !usedFallback) {
        usedFallback = true;
        console.warn("No se pudo cargar el mapa base; se usa un fondo simple.", event.error);
        map.setStyle(FALLBACK_STYLE);
      }
    });
    map.on("style.load", () => setStyleVersion((v) => v + 1));
    map.on("click", (event) => {
      dispatch({ type: "setPoint", point: { lat: event.lngLat.lat, lon: event.lngLat.lng } });
    });
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [dispatch]);

  // Capa de datos.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || !layer) return;
    const display = VARIABLES[layer.variable].display;
    if (map.getLayer(DATA_LAYER)) map.removeLayer(DATA_LAYER);
    if (map.getSource(DATA_SOURCE)) map.removeSource(DATA_SOURCE);

    if (layer.layer.kind === "grid" && layer.layer.grid) {
      map.addSource(DATA_SOURCE, {
        type: "image",
        url: gridToImage(layer.layer.grid, display),
        coordinates: gridCorners(layer.layer.grid),
      });
    } else if (layer.layer.kind === "tiles" && layer.layer.tiles) {
      map.addSource(DATA_SOURCE, {
        type: "raster",
        tiles: layer.layer.tiles,
        tileSize: layer.layer.tile_size ?? 256,
        bounds: layer.layer.bounds as [number, number, number, number] | undefined,
        attribution: layer.layer.attribution,
      });
    } else {
      return;
    }
    map.addLayer(
      {
        id: DATA_LAYER,
        type: "raster",
        source: DATA_SOURCE,
        paint: { "raster-opacity": 0.9, "raster-resampling": "nearest", "raster-fade-duration": 0 },
        layout: { visibility: state.layers.data ? "visible" : "none" },
      },
      firstLabelLayer(map),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [layer, styleVersion]);

  useEffect(() => {
    const map = mapRef.current;
    if (map && ready && map.getLayer(DATA_LAYER)) {
      map.setLayoutProperty(DATA_LAYER, "visibility", state.layers.data ? "visible" : "none");
    }
  }, [state.layers.data, styleVersion]);

  // Límites estatales.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const controller = new AbortController();
    const id = "limites-estados";
    if (!state.layers.states) {
      if (map.getLayer(id)) map.setLayoutProperty(id, "visibility", "none");
      return;
    }
    if (map.getLayer(id)) {
      map.setLayoutProperty(id, "visibility", "visible");
      return;
    }
    api
      .regionsGeojson("state", undefined, controller.signal)
      .then((data) => {
        if (map.getSource(id)) return;
        map.addSource(id, { type: "geojson", data });
        map.addLayer({
          id,
          type: "line",
          source: id,
          paint: { "line-color": theme === "oscuro" ? "#9FB1B8" : "#4A625C", "line-width": 0.8, "line-opacity": 0.8 },
        });
        setBoundaryMessage(null);
      })
      .catch((error: Error) => {
        if (error.name !== "AbortError") setBoundaryMessage(error.message);
      });
    return () => controller.abort();
  }, [styleVersion, state.layers.states, theme]);

  // Límites municipales (solo del estado elegido, para no cargar todo el país).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const id = "limites-municipios";
    if (map.getLayer(id)) map.removeLayer(id);
    if (map.getSource(id)) map.removeSource(id);
    const stateCode = state.region?.code.slice(0, 2);
    if (!state.layers.municipalities || !stateCode) return;
    const controller = new AbortController();
    api
      .regionsGeojson("municipality", stateCode, controller.signal)
      .then((data) => {
        if (map.getSource(id)) return;
        map.addSource(id, { type: "geojson", data });
        map.addLayer({
          id,
          type: "line",
          source: id,
          paint: { "line-color": theme === "oscuro" ? "#6C8089" : "#7E948E", "line-width": 0.5 },
        });
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [styleVersion, state.layers.municipalities, state.region, theme]);

  // Contorno de la región seleccionada.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const id = "region-seleccionada";
    const empty: GeoJSON.FeatureCollection = { type: "FeatureCollection", features: [] };
    if (!map.getSource(id)) {
      map.addSource(id, { type: "geojson", data: empty });
      map.addLayer({ id, type: "line", source: id, paint: { "line-color": "#1E9C96", "line-width": 2.5 } });
    }
    const source = map.getSource(id) as GeoJSONSource;
    if (!state.region) {
      source.setData(empty);
      return;
    }
    const controller = new AbortController();
    const level = state.region.level;
    api
      .regionsGeojson(level, level === "municipality" ? state.region.code.slice(0, 2) : undefined, controller.signal)
      .then((data) => {
        const feature = data.features.find((f) => f.properties?.code === state.region?.code);
        source.setData(feature ? { type: "FeatureCollection", features: [feature] } : empty);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [styleVersion, state.region]);

  // Marcador del punto consultado.
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    if (!state.point) {
      markerRef.current?.remove();
      markerRef.current = null;
      return;
    }
    if (!markerRef.current) {
      const el = document.createElement("div");
      el.className = "size-4 rounded-full border-[3px] border-white bg-[#1E9C96] shadow";
      el.setAttribute("aria-hidden", "true");
      markerRef.current = new maplibregl.Marker({ element: el });
    }
    markerRef.current.setLngLat([state.point.lon, state.point.lat]).addTo(map);
  }, [state.point]);

  const queryCenter = () => {
    const center = mapRef.current?.getCenter();
    if (center) dispatch({ type: "setPoint", point: { lat: center.lat, lon: center.lng } });
  };

  const downloadImage = () => {
    const canvas = mapRef.current?.getCanvas();
    if (!canvas) return;
    const link = document.createElement("a");
    link.download = `atlas_${state.variable}_${state.date.year}-${String(state.date.month).padStart(2, "0")}.png`;
    link.href = canvas.toDataURL("image/png");
    link.click();
  };

  // Mantener el contorno de imagen al cambiar de tamaño.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !container.current) return;
    const observer = new ResizeObserver(() => map.resize());
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);

  const variable = VARIABLES[state.variable];
  return (
    <div className="relative min-h-[320px] w-full flex-1 overflow-hidden rounded-[20px] border border-borde bg-[#D9E7EA]">
      {/* Posición en línea (no con clases de Tailwind): maplibre-gl.css pone
          `.maplibregl-map { position: relative }` fuera de @layer y le gana a
          `absolute`, lo que deja el contenedor con 0 px de alto. */}
      <div
        ref={container}
        style={{ position: "absolute", inset: 0 }}
        role="region"
        aria-label={`Mapa de ${variable.name.toLowerCase()} en México. Haz clic en un lugar para consultar su valor.`}
      />
      <div className="absolute bottom-3 right-3 flex gap-2">
        <Button size="sm" variant="secondary" className="bg-panel/95" onClick={queryCenter}>
          <Crosshair aria-hidden="true" />
          Consultar el centro
        </Button>
        <Button size="sm" variant="secondary" className="bg-panel/95" onClick={downloadImage} aria-label="Descargar imagen del mapa">
          <ImageDown aria-hidden="true" />
        </Button>
      </div>
      {boundaryMessage && state.layers.states && (
        <p className="absolute top-3 left-3 max-w-xs rounded-xl bg-panel/95 px-3 py-2 text-xs text-texto-suave">
          Límites estatales no disponibles: {boundaryMessage}
        </p>
      )}
    </div>
  );
}

