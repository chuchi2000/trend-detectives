/**
 * Cliente de la API REST (FastAPI).
 *
 * Todas las llamadas pasan por `request`, que convierte los errores del
 * backend ({"error": {"code", "message"}}) en ApiError con un mensaje en
 * español listo para mostrarse. Las credenciales de NASA nunca pasan por aquí.
 */
import type { VariableId } from "@/config/variables";
import type {
  ApiErrorBody,
  CompareResponse,
  CorrelationResponse,
  HealthResponse,
  LayerResponse,
  MetadataResponse,
  PointResponse,
  RegionsResponse,
  StatisticsResponse,
  TimeSeriesResponse,
  VariablesResponse,
} from "@/services/types";

const BASE_URL = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

type Params = Record<string, string | number | boolean | null | undefined>;

export function buildUrl(path: string, params: Params = {}): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== "") search.set(key, String(value));
  }
  const query = search.toString();
  return `${BASE_URL}/api${path}${query ? `?${query}` : ""}`;
}

async function request<T>(path: string, params: Params = {}, signal?: AbortSignal): Promise<T> {
  let response: Response;
  try {
    response = await fetch(buildUrl(path, params), { signal, headers: { Accept: "application/json" } });
  } catch (error) {
    if ((error as Error).name === "AbortError") throw error;
    throw new ApiError(
      "No se pudo conectar con el servidor del Atlas. Revisa que el backend esté en marcha.",
      "sin_conexion",
      0,
    );
  }
  if (!response.ok) {
    let body: ApiErrorBody | { detail?: unknown } | null = null;
    try {
      body = await response.json();
    } catch {
      body = null;
    }
    if (body && "error" in body) throw new ApiError(body.error.message, body.error.code, response.status);
    throw new ApiError(
      response.status === 422
        ? "Los parámetros de la consulta no son válidos."
        : `El servidor respondió con un error (${response.status}).`,
      "error_http",
      response.status,
    );
  }
  return (await response.json()) as T;
}

export interface Target {
  lat?: number | null;
  lon?: number | null;
  region?: string | null;
}

export const api = {
  health: (signal?: AbortSignal) => request<HealthResponse>("/health", {}, signal),
  variables: (signal?: AbortSignal) => request<VariablesResponse>("/variables", {}, signal),
  metadata: (variable: VariableId, signal?: AbortSignal) =>
    request<MetadataResponse>(`/metadata/${variable}`, {}, signal),
  layer: (variable: VariableId, year: number, month: number, signal?: AbortSignal) =>
    request<LayerResponse>(`/layers/${variable}`, { year, month }, signal),
  point: (variable: VariableId, year: number, month: number, lat: number, lon: number, signal?: AbortSignal) =>
    request<PointResponse>("/point", { variable, year, month, lat, lon }, signal),
  statistics: (variable: VariableId, year: number, month: number, region: string, signal?: AbortSignal) =>
    request<StatisticsResponse>("/statistics", { variable, year, month, region }, signal),
  timeseries: (variable: VariableId, target: Target, range: { start?: string; end?: string } = {}, signal?: AbortSignal) =>
    request<TimeSeriesResponse>("/timeseries", { variable, ...target, ...range }, signal),
  correlation: (a: VariableId, b: VariableId, target: Target, signal?: AbortSignal) =>
    request<CorrelationResponse>("/correlation", { a, b, ...target }, signal),
  compare: (variable: VariableId, a: string, b: string, region: string, signal?: AbortSignal) =>
    request<CompareResponse>("/compare", { variable, a, b, region }, signal),
  regions: (level: "state" | "municipality", state?: string, signal?: AbortSignal) =>
    request<RegionsResponse>("/regions", { level, estado: state }, signal),
  regionsGeojson: (level: "state" | "municipality", state?: string, signal?: AbortSignal) =>
    request<GeoJSON.FeatureCollection>("/regions/geojson", { level, estado: state }, signal),
};

export const exportUrls = {
  timeseriesCsv: (variable: VariableId, target: Target) => buildUrl("/export/timeseries.csv", { variable, ...target }),
  statisticsCsv: (variable: VariableId, year: number, month: number, region: string) =>
    buildUrl("/export/statistics.csv", { variable, year, month, region }),
  raster: (variable: VariableId, year: number, month: number) => buildUrl("/export/raster", { variable, year, month }),
};
