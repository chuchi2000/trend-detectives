import { MapPin, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES } from "@/config/variables";
import { useApi } from "@/hooks/useApi";
import { classIndex } from "@/lib/classify";
import { humanYm } from "@/lib/dates";
import { formatCoord, formatNumber } from "@/lib/format";
import { api } from "@/services/api";

/**
 * Valor de la variable en el punto elegido en el mapa.
 * En Explorador se explica con palabras; en Científico, con cifra, celda y resolución.
 */
export function PointReadout() {
  const { state, dispatch } = useAtlas();
  const { point, variable, date, mode } = state;
  const result = useApi(
    point ? (signal) => api.point(variable, date.year, date.month, point.lat, point.lon, signal) : null,
    [point?.lat, point?.lon, variable, date.year, date.month],
  );
  if (!point) {
    return (
      <p className="flex items-center gap-2 text-sm text-texto-suave">
        <MapPin aria-hidden="true" className="size-4 text-acento" />
        Haz clic en el mapa para consultar el valor de un lugar.
      </p>
    );
  }
  const v = VARIABLES[variable];
  const value = result.data?.display_value ?? null;
  const level = value === null ? null : classIndex(value, v.display.breaks);
  const words =
    level === null ? null : level <= 2 ? "bajo" : level <= 5 ? "intermedio" : "alto";

  return (
    <section aria-live="polite" className="flex flex-col gap-2 rounded-2xl border border-borde bg-panel p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-display text-sm font-semibold text-texto">Lugar consultado</p>
          <p className="font-display text-xs text-texto-suave font-semicondensada cifras">{formatCoord(point.lat, point.lon)}</p>
        </div>
        <Button size="icon" variant="ghost" aria-label="Quitar el punto" onClick={() => dispatch({ type: "setPoint", point: null })}>
          <X aria-hidden="true" />
        </Button>
      </div>
      {result.status === "loading" && <p className="text-sm text-texto-suave">Consultando…</p>}
      {result.status === "error" && <StatusMessage kind="error">{result.error.message}</StatusMessage>}
      {result.status === "success" &&
        (value === null ? (
          <p className="text-sm text-texto-suave">
            Sin dato en este lugar para {humanYm(date)} (fuera del territorio, nubes o superficie que el producto no
            calcula).
          </p>
        ) : mode === "explorador" ? (
          <p className="text-[15px] leading-relaxed text-texto">
            En {humanYm(date)}, aquí el valor fue <strong>{words}</strong> comparado con la escala del mapa:{" "}
            <strong className="cifras">
              {formatNumber(value)} {v.display.displayUnit}
            </strong>
            .
          </p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-texto-suave">Valor</dt>
            <dd className="font-display font-semibold font-semicondensada cifras">
              {formatNumber(value, 2)} {v.display.displayUnit}
            </dd>
            <dt className="text-texto-suave">Celda</dt>
            <dd className="font-display font-semicondensada cifras">
              {result.data.cell ? formatCoord(result.data.cell.lat, result.data.cell.lon) : "—"}
            </dd>
            <dt className="text-texto-suave">Resolución</dt>
            <dd className="font-display font-semicondensada">{result.data.resolution}</dd>
          </dl>
        ))}
    </section>
  );
}
