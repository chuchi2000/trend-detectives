/**
 * Mezcla `overlay` sobre `base` (misma regla que backend/app/core/i18n.py):
 * objetos clave por clave, listas de objetos elemento por elemento; cualquier
 * otro valor se reemplaza. Las claves que empiezan con "_" se ignoran.
 */
export function deepMerge(base: unknown, overlay: unknown): unknown {
  const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null && !Array.isArray(v);
  if (isObject(base) && isObject(overlay)) {
    const merged: Record<string, unknown> = { ...base };
    for (const [key, value] of Object.entries(overlay)) {
      if (key.startsWith("_")) continue;
      merged[key] = key in base ? deepMerge(base[key], value) : value;
    }
    return merged;
  }
  if (Array.isArray(base) && Array.isArray(overlay) && [...base, ...overlay].every(isObject)) {
    return base.map((item, i) => (i < overlay.length ? deepMerge(item, overlay[i]) : item));
  }
  return overlay;
}
