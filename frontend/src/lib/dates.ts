/**
 * Utilidades de fechas mensuales. Un mes se representa como "AAAA-MM" o como
 * índice entero (año × 12 + mes − 1), igual que en el backend.
 */

export const MONTHS_ES = [
  "enero",
  "febrero",
  "marzo",
  "abril",
  "mayo",
  "junio",
  "julio",
  "agosto",
  "septiembre",
  "octubre",
  "noviembre",
  "diciembre",
] as const;

export interface YearMonth {
  year: number;
  month: number;
}

export function ymIndex({ year, month }: YearMonth): number {
  return year * 12 + (month - 1);
}

export function fromIndex(index: number): YearMonth {
  return { year: Math.floor(index / 12), month: (index % 12) + 1 };
}

export function parseYm(text: string): YearMonth {
  const match = /^(\d{4})-(\d{2})$/.exec(text);
  if (!match) throw new Error(`Fecha inválida: ${text}`);
  return { year: Number(match[1]), month: Number(match[2]) };
}

export function formatYm({ year, month }: YearMonth): string {
  return `${year}-${String(month).padStart(2, "0")}`;
}

export function humanYm(value: YearMonth | string): string {
  const ym = typeof value === "string" ? parseYm(value) : value;
  return `${MONTHS_ES[ym.month - 1]} de ${ym.year}`;
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}

export interface Range {
  start: string;
  end: string;
}

export function inRange(ym: YearMonth, range: Range): boolean {
  const i = ymIndex(ym);
  return i >= ymIndex(parseYm(range.start)) && i <= ymIndex(parseYm(range.end));
}

/** Lleva una fecha al mes disponible más cercano. */
export function clampToRange(ym: YearMonth, range: Range): YearMonth {
  const i = ymIndex(ym);
  const lo = ymIndex(parseYm(range.start));
  const hi = ymIndex(parseYm(range.end));
  return fromIndex(Math.min(Math.max(i, lo), hi));
}

/** Avanza `step` meses sin salir del rango; devuelve null si ya está en el borde. */
export function stepWithin(ym: YearMonth, step: number, range: Range): YearMonth | null {
  const next = ymIndex(ym) + step;
  const lo = ymIndex(parseYm(range.start));
  const hi = ymIndex(parseYm(range.end));
  if (next < lo || next > hi) return null;
  return fromIndex(next);
}

export function yearsOf(range: Range): number[] {
  const a = parseYm(range.start).year;
  const b = parseYm(range.end).year;
  return Array.from({ length: b - a + 1 }, (_, k) => a + k);
}
