import { VARIABLES, type Mode, type VariableId } from "@/config/variables";
import { classLabels } from "@/lib/classify";
import { cn } from "@/lib/utils";

/**
 * Leyenda del mapa. Misma escala de 9 clases en ambos modos:
 * - Explorador: palabras en los extremos ("Menos lluvia" / "Más lluvia").
 * - Científico: límites de cada clase y unidad.
 * Siempre incluye la muestra de "Sin dato" (rayado), que nunca es cero.
 */
export function MapLegend({ variable, mode }: { variable: VariableId; mode: Mode }) {
  const v = VARIABLES[variable];
  const labels = classLabels(v.display);
  return (
    <figure className="flex flex-col gap-1.5" aria-label={`Leyenda de ${v.name}`}>
      <div className="flex items-end gap-3">
        <ol className="grid flex-1 grid-cols-9 gap-0.5 rounded-md border border-borde bg-panel p-0.5">
          {v.display.ramp.map((color, i) => (
            <li key={color} className="flex flex-col items-center gap-1">
              <span className="block h-3.5 w-full rounded-[2px]" style={{ backgroundColor: color }} />
              <span className="sr-only">
                Clase {i + 1}: {labels[i]} {v.display.displayUnit}
              </span>
            </li>
          ))}
        </ol>
        <div className="flex items-center gap-1.5">
          <span className="rayado-sin-dato block h-4 w-6 rounded-[3px] border border-borde-fuerte" />
          <span className="text-xs text-texto-suave">Sin dato</span>
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
          <span className="font-display text-xs text-texto-suave font-semicondensada">Unidad: {v.display.displayUnit}</span>
        </figcaption>
      )}
    </figure>
  );
}
