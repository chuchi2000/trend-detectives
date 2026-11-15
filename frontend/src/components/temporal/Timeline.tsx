import { useAtlas } from "@/context/AtlasStateContext";
import { STUDY_PERIOD, VARIABLES } from "@/config/variables";
import { inRange, yearsOf } from "@/lib/dates";
import { cn } from "@/lib/utils";

/**
 * Barra cronológica 2000–2025. Cada año es un botón; los años sin datos de la
 * variable aparecen rayados y desactivados. El año consultado se resalta.
 */
export function Timeline() {
  const { state, dispatch } = useAtlas();
  const variable = VARIABLES[state.variable];
  const years = yearsOf(STUDY_PERIOD);

  return (
    <nav aria-label="Barra cronológica" className="flex flex-col gap-1">
      <div className="flex gap-[3px]">
        {years.map((year) => {
          const any = Array.from({ length: 12 }, (_, i) => inRange({ year, month: i + 1 }, variable.availability)).some(Boolean);
          const current = year === state.date.year;
          const compared = state.compare.enabled && year === state.compare.date.year;
          return (
            <button
              key={year}
              type="button"
              disabled={!any}
              aria-current={current ? "date" : undefined}
              aria-label={any ? `Ir a ${year}` : `${year}: sin datos de ${variable.shortLabel}`}
              title={any ? String(year) : `${year}: sin datos`}
              onClick={() => dispatch({ type: "setDate", date: { year, month: state.date.month } })}
              className={cn(
                "h-7 min-w-0 flex-1 rounded-[4px] transition-colors",
                !any && "rayado-sin-dato cursor-not-allowed",
                any && !current && "bg-panel-2 hover:bg-borde",
                current && "bg-acento",
                compared && !current && "ring-2 ring-acento ring-inset",
              )}
            />
          );
        })}
      </div>
      <div aria-hidden="true" className="flex justify-between font-display text-xs font-medium text-texto-suave font-semicondensada cifras">
        <span>2000</span>
        <span>2005</span>
        <span>2010</span>
        <span>2015</span>
        <span>2020</span>
        <span>2025</span>
      </div>
    </nav>
  );
}
