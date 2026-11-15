/**
 * Estado compartido del Atlas: lo que la persona está consultando.
 *
 * Los dos modos leen y escriben ESTE mismo estado. Cambiar de modo solo cambia
 * `mode`; la variable, la fecha, la región, el punto y las capas se conservan.
 * El estado se refleja en la URL (?modo=...&variable=...), así un enlace
 * copiado abre exactamente la misma consulta.
 *
 * Este archivo es lógica pura (sin React) para poder probarlo fácilmente.
 */
import { VARIABLES, isVariableId, type Mode, type VariableId } from "@/config/variables";
import { clampToRange, formatYm, humanYm, inRange, stepWithin, type YearMonth } from "@/lib/dates";

export interface RegionSelection {
  level: "state" | "municipality";
  code: string;
  name: string;
}

export interface LayerVisibility {
  data: boolean;
  states: boolean;
  municipalities: boolean;
}

export interface AtlasState {
  mode: Mode;
  variable: VariableId;
  date: YearMonth;
  compare: { enabled: boolean; date: YearMonth };
  region: RegionSelection | null;
  point: { lat: number; lon: number } | null;
  layers: LayerVisibility;
  notice: string | null;
}

export type AtlasAction =
  | { type: "setMode"; mode: Mode }
  | { type: "setVariable"; variable: VariableId }
  | { type: "setDate"; date: YearMonth }
  | { type: "stepMonth"; step: number }
  | { type: "toggleCompare" }
  | { type: "setCompareDate"; date: YearMonth }
  | { type: "setRegion"; region: RegionSelection | null }
  | { type: "setPoint"; point: { lat: number; lon: number } | null }
  | { type: "toggleLayer"; layer: keyof LayerVisibility }
  | { type: "dismissNotice" }
  | { type: "replace"; state: AtlasState };

export const DEFAULT_STATE: AtlasState = {
  mode: "explorador",
  variable: "precipitation",
  date: { year: 2015, month: 7 },
  compare: { enabled: false, date: { year: 2005, month: 7 } },
  region: null,
  point: null,
  layers: { data: true, states: true, municipalities: false },
  notice: null,
};

function adjustDate(variable: VariableId, date: YearMonth): { date: YearMonth; notice: string | null } {
  const availability = VARIABLES[variable].availability;
  if (inRange(date, availability)) return { date, notice: null };
  const clamped = clampToRange(date, availability);
  return {
    date: clamped,
    notice:
      `${VARIABLES[variable].name} no tiene datos para ${humanYm(date)}. ` +
      `Mostramos ${humanYm(clamped)}; hay datos de ${humanYm(availability.start)} a ${humanYm(availability.end)}.`,
  };
}

export function atlasReducer(state: AtlasState, action: AtlasAction): AtlasState {
  switch (action.type) {
    case "setMode":
      return { ...state, mode: action.mode };
    case "setVariable": {
      const { date, notice } = adjustDate(action.variable, state.date);
      const compare = adjustDate(action.variable, state.compare.date);
      return { ...state, variable: action.variable, date, notice, compare: { ...state.compare, date: compare.date } };
    }
    case "setDate": {
      const { date, notice } = adjustDate(state.variable, action.date);
      return { ...state, date, notice };
    }
    case "stepMonth": {
      const next = stepWithin(state.date, action.step, VARIABLES[state.variable].availability);
      if (!next) {
        return { ...state, notice: "Llegaste al límite de los datos disponibles para esta variable." };
      }
      return { ...state, date: next, notice: null };
    }
    case "toggleCompare":
      return { ...state, compare: { ...state.compare, enabled: !state.compare.enabled } };
    case "setCompareDate": {
      const { date } = adjustDate(state.variable, action.date);
      return { ...state, compare: { ...state.compare, date } };
    }
    case "setRegion":
      return { ...state, region: action.region };
    case "setPoint":
      return { ...state, point: action.point };
    case "toggleLayer":
      return { ...state, layers: { ...state.layers, [action.layer]: !state.layers[action.layer] } };
    case "dismissNotice":
      return { ...state, notice: null };
    case "replace":
      return action.state;
  }
}

// ---- URL ------------------------------------------------------------------

export function stateToSearch(state: AtlasState): string {
  const params = new URLSearchParams();
  params.set("modo", state.mode);
  params.set("variable", state.variable);
  params.set("fecha", formatYm(state.date));
  if (state.compare.enabled) params.set("comparar", formatYm(state.compare.date));
  if (state.region) params.set("region", `${state.region.level === "state" ? "estado" : "municipio"}:${state.region.code}`);
  if (state.region) params.set("nombre", state.region.name);
  if (state.point) params.set("punto", `${state.point.lat.toFixed(4)},${state.point.lon.toFixed(4)}`);
  const hidden = (Object.keys(state.layers) as Array<keyof LayerVisibility>).filter(
    (k) => state.layers[k] !== DEFAULT_STATE.layers[k],
  );
  if (hidden.length) params.set("capas", hidden.map((k) => `${k}:${state.layers[k] ? 1 : 0}`).join(","));
  return `?${params.toString()}`;
}

function parseDate(text: string | null): YearMonth | null {
  if (!text) return null;
  const match = /^(\d{4})-(\d{2})$/.exec(text);
  if (!match) return null;
  const month = Number(match[2]);
  if (month < 1 || month > 12) return null;
  return { year: Number(match[1]), month };
}

export function stateFromSearch(search: string, base: AtlasState = DEFAULT_STATE): AtlasState {
  const params = new URLSearchParams(search);
  const mode = params.get("modo");
  const variableParam = params.get("variable");
  const variable = isVariableId(variableParam) ? variableParam : base.variable;
  const date = adjustDate(variable, parseDate(params.get("fecha")) ?? base.date).date;
  const compareDate = parseDate(params.get("comparar"));

  let region: RegionSelection | null = null;
  const regionMatch = /^(estado|municipio):(\d{2,5})$/.exec(params.get("region") ?? "");
  if (regionMatch) {
    region = {
      level: regionMatch[1] === "estado" ? "state" : "municipality",
      code: regionMatch[2] as string,
      name: params.get("nombre") ?? regionMatch[2] ?? "",
    };
  }

  let point: AtlasState["point"] = null;
  const pointMatch = /^(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)$/.exec(params.get("punto") ?? "");
  if (pointMatch) point = { lat: Number(pointMatch[1]), lon: Number(pointMatch[2]) };

  const layers = { ...base.layers };
  for (const item of (params.get("capas") ?? "").split(",")) {
    const [key, value] = item.split(":");
    if (key && key in layers) layers[key as keyof LayerVisibility] = value === "1";
  }

  return {
    ...base,
    mode: mode === "cientifico" || mode === "explorador" ? mode : base.mode,
    variable,
    date,
    compare: compareDate
      ? { enabled: true, date: adjustDate(variable, compareDate).date }
      : { ...base.compare, enabled: false },
    region,
    point,
    layers,
    notice: null,
  };
}

/** Texto de región que espera la API: "nacional", "estado:24" o "municipio:24028". */
export function regionParam(region: RegionSelection | null): string {
  if (!region) return "nacional";
  return `${region.level === "state" ? "estado" : "municipio"}:${region.code}`;
}
