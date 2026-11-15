/** Formato de números para México: punto decimal y espacio fino para miles. */
export function formatNumber(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  const fixed = Math.abs(value) >= 100 ? value.toFixed(0) : value.toFixed(digits);
  const [int, dec] = fixed.split(".");
  const grouped = (int ?? "").replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return dec ? `${grouped}.${dec}` : grouped;
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return `${(value * 100).toFixed(digits)} %`;
}

export function formatCoord(lat: number, lon: number): string {
  const ns = lat >= 0 ? "N" : "S";
  const eo = lon >= 0 ? "E" : "O";
  return `${Math.abs(lat).toFixed(2)}° ${ns}, ${Math.abs(lon).toFixed(2)}° ${eo}`;
}
