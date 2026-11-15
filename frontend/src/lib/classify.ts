import type { VariableDisplay } from "@/config/variables";
import { formatNumber } from "@/lib/format";

/** Índice de clase (0–8) de un valor en unidades de visualización. */
export function classIndex(value: number, breaks: number[]): number {
  let index = 0;
  while (index < breaks.length && value >= (breaks[index] as number)) index += 1;
  return index;
}

export function colorFor(value: number | null, display: VariableDisplay): string | null {
  if (value === null || !Number.isFinite(value)) return null;
  return display.ramp[classIndex(value, display.breaks)] ?? null;
}

/** Etiquetas de cada clase: "< 5", "5–15", …, "≥ 250". */
export function classLabels(display: VariableDisplay): string[] {
  const b = display.breaks;
  return display.ramp.map((_, i) => {
    if (i === 0) return `< ${formatNumber(b[0], 1)}`;
    if (i === b.length) return `≥ ${formatNumber(b[b.length - 1], 1)}`;
    return `${formatNumber(b[i - 1], 1)}–${formatNumber(b[i], 1)}`;
  });
}

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)];
}
