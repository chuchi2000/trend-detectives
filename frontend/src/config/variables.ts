/**
 * Registro de variables del frontend.
 *
 * La información científica (producto, disponibilidad, escalas) sale del MISMO
 * archivo que usa el backend: metadata/sources/products.json. Aquí solo se
 * agregan detalles de presentación. Para cambiar una escala de color, sus
 * cortes o las fechas disponibles, edita products.json y ambos lados cambian.
 */
import products from "@metadata/sources/products.json";

import type { Range } from "@/lib/dates";

export type VariableId = "precipitation" | "no2" | "evapotranspiration" | "temperature";
export type Mode = "explorador" | "cientifico";

export const VARIABLE_IDS: VariableId[] = ["precipitation", "no2", "evapotranspiration", "temperature"];

export interface VariableDisplay {
  scale: number;
  displayUnit: string;
  breaks: number[];
  ramp: string[];
  identityColor: string;
  words: { low: string; high: string };
}

export interface VariableConfig {
  id: VariableId;
  name: string;
  shortLabel: string;
  unit: string;
  unitLong: string;
  dataType: string;
  product: { shortName: string; version: string; provider: string; mission: string; instrument: string };
  nativeResolution: string;
  nativeTemporal: string;
  availability: Range;
  display: VariableDisplay;
  caveats: string[];
}

type RawVariable = (typeof products.variables)[VariableId];

function toConfig(id: VariableId, raw: RawVariable): VariableConfig {
  return {
    id,
    name: raw.name,
    shortLabel: raw.short_label,
    unit: raw.unit,
    unitLong: raw.unit_long,
    dataType: raw.data_type,
    product: {
      shortName: raw.product.short_name,
      version: raw.product.version,
      provider: raw.product.provider,
      mission: raw.product.mission,
      instrument: raw.product.instrument,
    },
    nativeResolution: raw.spatial.native_resolution,
    nativeTemporal: raw.temporal.native_resolution,
    availability: { start: raw.temporal.available_start, end: raw.temporal.available_end },
    display: {
      scale: Number(raw.display.scale),
      displayUnit: raw.display.display_unit,
      breaks: raw.display.breaks,
      ramp: raw.display.ramp,
      identityColor: raw.display.identity_color,
      words: raw.display.words,
    },
    caveats: raw.caveats,
  };
}

export const VARIABLES: Record<VariableId, VariableConfig> = {
  precipitation: toConfig("precipitation", products.variables.precipitation),
  no2: toConfig("no2", products.variables.no2),
  evapotranspiration: toConfig("evapotranspiration", products.variables.evapotranspiration),
  temperature: toConfig("temperature", products.variables.temperature),
};

export const STUDY_PERIOD: Range = products.study_period;
export const COMPARISON_PERIOD: Range = {
  start: products.comparison_period.start,
  end: products.comparison_period.end,
};
export const COMMON_GRID = {
  bounds: products.common_grid.bounds as [number, number, number, number],
  resolution: products.common_grid.resolution_deg,
};

/** Centro y encuadre inicial del mapa (todo México). */
export const MEXICO_VIEW = {
  center: [-102.0, 23.6] as [number, number],
  bounds: [
    [-118.4, 14.4],
    [-86.6, 32.8],
  ] as [[number, number], [number, number]],
};

export function isVariableId(value: string | null): value is VariableId {
  return value !== null && (VARIABLE_IDS as string[]).includes(value);
}
