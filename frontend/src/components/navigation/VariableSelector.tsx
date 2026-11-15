import { VariableIcon } from "@/components/icons/VariableIcon";
import { VARIABLES, VARIABLE_IDS, type VariableId } from "@/config/variables";
import { cn } from "@/lib/utils";

/**
 * Selector de las cuatro variables. El botón seleccionado toma el color de
 * identidad de la variable (el mismo de su escala en el mapa).
 */
export function VariableSelector({ value, onChange }: { value: VariableId; onChange: (id: VariableId) => void }) {
  return (
    <div
      role="group"
      aria-label="Variable que se muestra en el mapa"
      className="-mx-4 flex gap-2 overflow-x-auto px-4 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0"
    >
      {VARIABLE_IDS.map((id) => {
        const v = VARIABLES[id];
        const selected = id === value;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={selected}
            onClick={() => onChange(id)}
            style={selected ? { backgroundColor: v.display.identityColor, borderColor: v.display.identityColor } : undefined}
            className={cn(
              "inline-flex min-h-11 shrink-0 items-center gap-2 rounded-full border-[1.5px] pr-4 pl-3 font-display text-[15px] font-semibold transition-colors",
              selected ? "text-white" : "border-borde-fuerte bg-panel text-texto hover:bg-panel-2",
            )}
          >
            <VariableIcon variable={id} />
            {v.shortLabel}
          </button>
        );
      })}
    </div>
  );
}
