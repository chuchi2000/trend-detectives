/**
 * Tipos de las respuestas de la API. Reflejan los modelos Pydantic de
 * backend/app/schemas/models.py: si cambias uno, cambia el otro.
 */
import type { VariableId } from "@/config/variables";

export type DataMode = "demo" | "real";

export interface Availability {
  start: string;
  end: string;
  processed?: string[] | null;
}

export interface Link {
  label: string;
  url: string;
}

export interface VariableInfo {
  id: VariableId;
  name: string;
  short_label: string;
  unit: string;
  unit_long: string;
  data_type: string;
  product: Record<string, unknown>;
  temporal: Record<string, unknown>;
  spatial: Record<string, unknown>;
  availability: Availability;
  processing: Record<string, string>;
  display: Record<string, unknown>;
  caveats: string[];
  sources: Link[];
}

export interface VariablesResponse {
  mode: DataMode;
  study_period: Availability;
  comparison_period: Availability;
  variables: VariableInfo[];
}

export interface MetadataResponse {
  mode: DataMode;
  variable: VariableInfo;
  layers: Array<Record<string, unknown>>;
  special_values: Record<string, string> | null;
  audit_date: string;
}

export interface Quality {
  coverage: number | null;
  n_valid: number | null;
  flags: string[];
  notes: string[];
  details?: Record<string, unknown>;
}

export interface GridPayload {
  west: number;
  south: number;
  east: number;
  north: number;
  res: number;
  nx: number;
  ny: number;
  values: Array<number | null>;
}

export interface ImagePayload {
  /** Ruta del PNG relativa a la API (empieza con /api). */
  url: string;
  /** Esquinas [lon, lat]: arriba-izq., arriba-der., abajo-der., abajo-izq. */
  coordinates: number[][];
}

export interface LayerRef {
  kind: "grid" | "tiles" | "image";
  grid?: GridPayload | null;
  image?: ImagePayload | null;
  tiles?: string[] | null;
  tile_size?: number | null;
  bounds?: number[] | null;
  attribution: string;
}

export interface LayerResponse {
  mode: DataMode;
  variable: VariableId;
  date: string;
  unit: string;
  display_unit: string;
  scale: number;
  resolution: string;
  source: string;
  data_type: string;
  availability: Availability;
  quality: Quality;
  layer: LayerRef;
}

export interface Cell {
  lat: number;
  lon: number;
  res: number;
}

export interface PointResponse {
  mode: DataMode;
  variable: VariableId;
  date: string;
  lat: number;
  lon: number;
  value: number | null;
  unit: string;
  display_value: number | null;
  display_unit: string;
  cell: Cell | null;
  resolution: string;
}

export interface RegionRef {
  level: "national" | "state" | "municipality";
  code: string | null;
  name: string;
}

export interface Stats {
  mean: number | null;
  median: number | null;
  min: number | null;
  max: number | null;
  std: number | null;
  n_valid: number;
  n_cells: number;
  coverage: number;
}

export interface Extreme {
  lat: number;
  lon: number;
  value: number;
}

export interface StatisticsResponse {
  mode: DataMode;
  variable: VariableId;
  date: string;
  unit: string;
  region: RegionRef;
  stats: Stats;
  extremes: { min: Extreme | null; max: Extreme | null };
  method: string;
}

export interface SeriesPoint {
  date: string;
  value: number | null;
}

export type TrendVerdict = "solida" | "indicio" | "variabilidad";

export interface Trend {
  method: string;
  slope_per_decade: number;
  /** Intervalo de confianza de la pendiente de Sen, por década. */
  slope_ci_low_per_decade: number;
  slope_ci_high_per_decade: number;
  confidence: number;
  unit: string;
  intercept: number;
  /** Mann–Kendall corregido por autocorrelación. */
  p_value: number;
  p_value_uncorrected: number;
  kendall_s: number;
  z: number;
  autocorrelation_lag1: number;
  autocorrelation_factor: number;
  signal_to_noise: number | null;
  n_years: number;
  years: number[];
  annual_means: number[];
  significant: boolean;
  verdict: TrendVerdict;
  verdict_label: string;
  interpretation: string;
}

export interface TimeSeriesResponse {
  mode: DataMode;
  variable: VariableId;
  unit: string;
  target: Record<string, unknown>;
  start: string;
  end: string;
  points: SeriesPoint[];
  trend: Trend | null;
  /** Tendencia sobre anomalías mensuales (en unidades de visualización). */
  trend_monthly?: TrendMonthly | null;
  method: string;
}

/** Ver backend/app/schemas/models.py → TrendMonthly. */
export interface TrendMonthly {
  method: string;
  unit: string;
  slope_per_decade: number;
  ci95: [number, number];
  sen_slope_per_decade: number;
  pct_change_per_decade: number | null;
  /** Mann–Kendall con modificación de Hamed–Rao. */
  p_value: number;
  t_test_p_value: number;
  significant: boolean;
  direction: string;
  lag1_autocorrelation: number;
  effective_months: number;
  mean: number;
  months: number;
  start: string;
  end: string;
  verdict: TrendVerdict;
  verdict_label: string;
  sentence: string;
  notes: string[];
  dates: string[];
  anomalies: Array<number | null>;
  trend_line: number[];
}

/** Ver backend/app/schemas/models.py → TrendMapResponse. Listas en el orden de grid.values. */
export interface TrendMapResponse {
  mode: DataMode;
  variable: VariableId;
  start: string;
  end: string;
  unit: string;
  relative: boolean;
  grid: GridPayload;
  ci95_low: Array<number | null>;
  ci95_high: Array<number | null>;
  p_value: Array<number | null>;
  significant: boolean[];
  pct_change_per_decade: Array<number | null> | null;
  summary: {
    n_pixels: number;
    fraction_up: number | null;
    fraction_significant_up: number | null;
    fraction_significant_down: number | null;
    median_slope_per_decade: number | null;
  };
  method: string;
  notes: string[];
  seconds: number;
}

export interface CorrelationResponse {
  mode: DataMode;
  variables: VariableId[];
  target: Record<string, unknown>;
  start: string | null;
  end: string | null;
  n: number;
  n_effective: number | null;
  r: number | null;
  r2: number | null;
  p_value: number | null;
  ci_low: number | null;
  ci_high: number | null;
  confidence: number;
  method: string;
  note: string;
}

export interface CompareResponse {
  mode: DataMode;
  variable: VariableId;
  unit: string;
  region: RegionRef;
  a: { date: string; stats: Stats };
  b: { date: string; stats: Stats };
  difference_mean: number | null;
  percent_change: number | null;
  cells_increase_fraction: number | null;
  method: string;
}

export interface RegionItem {
  level: "state" | "municipality";
  code: string;
  name: string;
  state_code?: string | null;
}

export interface RegionsResponse {
  level: "state" | "municipality";
  available: boolean;
  message: string | null;
  items: RegionItem[];
}

export interface HealthResponse {
  status: "ok";
  mode: DataMode;
  version: string;
  boundaries_loaded: boolean;
  titiler_url: string | null;
}

export interface ApiErrorBody {
  error: { code: string; message: string };
}
