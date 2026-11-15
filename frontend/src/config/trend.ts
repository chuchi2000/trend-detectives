/**
 * Escala divergente del mapa de tendencia: azul si baja, blanco cerca de cero,
 * rojo si sube (ColorBrewer RdBu, 11 clases, apta para daltonismo rojo-verde).
 *
 * Los límites son fijos por variable para que la leyenda no dependa de los datos
 * y dos mapas de la misma variable se puedan comparar. Se eligieron cerca del
 * percentil 95 del |cambio por década| dentro de México con los datos reales;
 * lo que pase del límite se pinta con el color del extremo.
 */
import type { VariableId } from "@/config/variables";

export const TREND_RAMP = [
  "#053061",
  "#2166AC",
  "#4393C3",
  "#92C5DE",
  "#D1E5F0",
  "#F7F7F7",
  "#FDDBC7",
  "#F4A582",
  "#D6604D",
  "#B2182B",
  "#67001F",
] as const;

/** Cambio por década (unidades de visualización) que satura la escala. */
export const TREND_LIMITS: Record<VariableId, number> = {
  temperature: 1.2,
  precipitation: 12,
  evapotranspiration: 4,
  no2: 0.2,
};

/** Cortes simétricos: ±L·(0.1, 0.3, 0.5, 0.7, 0.9). La clase central (|v| < 0.1·L) es blanca. */
export function trendBreaks(limit: number): number[] {
  return [-0.9, -0.7, -0.5, -0.3, -0.1, 0.1, 0.3, 0.5, 0.7, 0.9].map((f) => f * limit);
}

/** Opacidad (0–255) de los píxeles significativos y de los que podrían ser casualidad. */
export const TREND_ALPHA = { significant: 240, notSignificant: 70 } as const;
