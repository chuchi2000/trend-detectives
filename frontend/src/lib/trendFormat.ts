import type { TrendVerdict } from "@/services/types";

/** Color de la etiqueta del veredicto de tendencia. */
export const VERDICT_TONE: Record<TrendVerdict, "accent" | "warning" | "neutral"> = {
  solida: "accent",
  indicio: "warning",
  variabilidad: "neutral",
};

/** Valor p legible: «< 0.001» para los muy pequeños. */
export function formatP(p: number): string {
  return p < 0.001 ? "< 0.001" : p.toFixed(3);
}
