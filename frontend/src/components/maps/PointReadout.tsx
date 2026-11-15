import { MapPin, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status";
import { useAtlas } from "@/context/AtlasStateContext";
import { useLanguage, useVariables } from "@/i18n/language";
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
  const { lang, t } = useLanguage();
  const variables = useVariables();
  const result = useApi(
    point ? (signal) => api.point(variable, date.year, date.month, point.lat, point.lon, signal) : null,
    [point?.lat, point?.lon, variable, date.year, date.month],
  );
  if (!point) {
    return (
      <p className="flex items-center gap-2 text-sm text-texto-suave">
        <MapPin aria-hidden="true" className="size-4 text-acento" />
        {t.point.prompt}
      </p>
    );
  }
  const v = variables[variable];
  const value = result.data?.display_value ?? null;
  const level = value === null ? null : classIndex(value, v.display.breaks);
  const words =
    level === null ? null : level <= 2 ? t.point.low : level <= 5 ? t.point.medium : t.point.high;

  return (
    <section aria-live="polite" className="flex flex-col gap-2 rounded-2xl border border-borde bg-panel p-4">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="font-display text-sm font-semibold text-texto">{t.point.title}</p>
          <p className="font-display text-xs text-texto-suave font-semicondensada cifras">{formatCoord(point.lat, point.lon, lang)}</p>
        </div>
        <Button size="icon" variant="ghost" aria-label={t.common.removePoint} onClick={() => dispatch({ type: "setPoint", point: null })}>
          <X aria-hidden="true" />
        </Button>
      </div>
      {result.status === "loading" && <p className="text-sm text-texto-suave">{t.point.querying}</p>}
      {result.status === "error" && <StatusMessage kind="error">{result.error.message}</StatusMessage>}
      {result.status === "success" &&
        (value === null ? (
          <p className="text-sm text-texto-suave">
            {t.point.noData(humanYm(date, lang))}
          </p>
        ) : mode === "explorador" ? (
          <p className="text-[15px] leading-relaxed text-texto">
            {t.point.explorerBefore(humanYm(date, lang))} <strong>{words}</strong> {t.point.explorerMiddle}{" "}
            <strong className="cifras">
              {formatNumber(value)} {v.display.displayUnit}
            </strong>
            .
          </p>
        ) : (
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
            <dt className="text-texto-suave">{t.point.value}</dt>
            <dd className="font-display font-semibold font-semicondensada cifras">
              {formatNumber(value, 2)} {v.display.displayUnit}
            </dd>
            <dt className="text-texto-suave">{t.point.cell}</dt>
            <dd className="font-display font-semicondensada cifras">
              {result.data.cell ? formatCoord(result.data.cell.lat, result.data.cell.lon, lang) : "—"}
            </dd>
            <dt className="text-texto-suave">{t.point.resolution}</dt>
            <dd className="font-display font-semicondensada">{result.data.resolution}</dd>
          </dl>
        ))}
    </section>
  );
}
