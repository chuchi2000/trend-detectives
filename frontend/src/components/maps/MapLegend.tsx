import { TrendLegend } from "@/components/maps/TrendLegend";
import { useAtlas } from "@/context/AtlasStateContext";
import type { Mode, VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";
import { classLabels } from "@/lib/classify";
import { cn } from "@/lib/utils";

/**
 * Leyenda del mapa. Misma escala de 9 clases en ambos modos:
 * - Explorador: palabras en los extremos ("Menos lluvia" / "Más lluvia").
 * - Científico: límites de cada clase y unidad.
 * Siempre incluye la muestra de "Sin dato" (rayado), que nunca es cero.
 * En la vista «Tendencia» muestra la escala divergente (TrendLegend).
 */
export function MapLegend({ variable, mode }: { variable: VariableId; mode: Mode }) {
  const { state } = useAtlas();
  if (state.mapView === "tendencia") return <TrendLegend variable={variable} mode={mode} />;
  return <ValueLegend variable={variable} mode={mode} />;
}

function ValueLegend({ variable, mode }: { variable: VariableId; mode: Mode }) {
  const { t } = useLanguage();
  const v = useVariables()[variable];
  const labels = classLabels(v.display);
  return (
    <figure className="flex flex-col gap-1.5" aria-label={t.legend.aria(v.name)}>
      <div className="flex items-end gap-3">
        <ol className="grid flex-1 grid-cols-9 gap-0.5 rounded-md border border-borde bg-panel p-0.5">
          {v.display.ramp.map((color, i) => (
            <li key={color} className="flex flex-col items-center gap-1">
              <span className="block h-3.5 w-full rounded-[2px]" style={{ backgroundColor: color }} />
              <span className="sr-only">
                {t.legend.classItem(i + 1, labels[i] ?? "", v.display.displayUnit)}
              </span>
            </li>
          ))}
        </ol>
        <div className="flex items-center gap-1.5">
          <span className="rayado-sin-dato block h-4 w-6 rounded-[3px] border border-borde-fuerte" />
          <span className="text-xs text-texto-suave">{t.common.noData}</span>
        </div>
      </div>
      {mode === "explorador" ? (
        <figcaption className="flex justify-between pr-[86px] text-sm text-texto">
          <span>{v.display.words.low}</span>
          <span>{v.display.words.high}</span>
        </figcaption>
      ) : (
        <figcaption className="flex flex-col gap-0.5">
          <div
            className={cn(
              "grid grid-cols-9 gap-0.5 pr-[86px] font-display text-[11px] leading-tight text-texto-suave font-semicondensada cifras",
            )}
          >
            {labels.map((label) => (
              <span key={label} className="text-center">
                {label}
              </span>
            ))}
          </div>
          <span className="font-display text-xs text-texto-suave font-semicondensada">{t.common.unit}: {v.display.displayUnit}</span>
        </figcaption>
      )}
    </figure>
  );
}
