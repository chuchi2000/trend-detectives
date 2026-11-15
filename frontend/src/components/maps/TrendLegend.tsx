import { TREND_LIMITS, TREND_RAMP } from "@/config/trend";
import type { Mode, VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";
import { formatNumber } from "@/lib/format";

/**
 * Leyenda del mapa de tendencia: escala divergente centrada en cero, nota sobre
 * los píxeles tenues (no significativos) y la muestra de «Sin dato».
 */
export function TrendLegend({ variable, mode }: { variable: VariableId; mode: Mode }) {
  const { t } = useLanguage();
  const v = useVariables()[variable];
  const limit = TREND_LIMITS[variable];
  const ticks = [-limit, -limit / 2, 0, limit / 2, limit];
  const digits = limit < 1 ? 2 : limit < 10 ? 1 : 0;
  const unit = `${v.display.displayUnit} ${t.common.perDecade}`;
  return (
    <figure className="flex flex-col gap-1.5" aria-label={t.legend.trendAria(v.name)}>
      <p className="font-display text-sm font-semibold text-texto">{t.legend.trendTitle}</p>
      <div className="flex items-end gap-3">
        <ol className="grid flex-1 grid-cols-11 gap-0.5 rounded-md border border-borde bg-panel p-0.5">
          {TREND_RAMP.map((color, i) => (
            <li key={color}>
              <span className="block h-3.5 w-full rounded-[2px]" style={{ backgroundColor: color }} />
              <span className="sr-only">
                {t.legend.trendClass(i < 5 ? t.legend.down : i === 5 ? t.legend.almostNoChange : t.legend.up, i + 1)}
              </span>
            </li>
          ))}
        </ol>
        <div className="flex items-center gap-1.5">
          <span className="rayado-sin-dato block h-4 w-6 rounded-[3px] border border-borde-fuerte" />
          <span className="text-xs text-texto-suave">{t.common.noData}</span>
        </div>
      </div>
      <figcaption className="flex flex-col gap-1">
        {mode === "explorador" ? (
          <div className="flex justify-between pr-[86px] text-sm text-texto">
            <span>{t.legend.down}</span>
            <span>{t.legend.noChange}</span>
            <span>{t.legend.up}</span>
          </div>
        ) : (
          <div className="flex justify-between pr-[86px] font-display text-[11px] text-texto-suave font-semicondensada cifras">
            {ticks.map((tick, i) => (
              <span key={tick}>
                {i === 0 ? "≤ " : i === ticks.length - 1 ? "≥ +" : tick > 0 ? "+" : ""}
                {formatNumber(tick, digits)}
              </span>
            ))}
          </div>
        )}
        <span className="font-display text-xs text-texto-suave font-semicondensada">{t.common.unit}: {unit}</span>
        <span className="flex items-center gap-2 text-xs text-texto-suave">
          <span className="block h-3 w-5 rounded-[2px] bg-[#D6604D]/30" aria-hidden="true" />
          {t.legend.faint}
        </span>
      </figcaption>
    </figure>
  );
}
