import { ChartLine, Compass } from "lucide-react";

import type { Mode } from "@/config/variables";
import { cn } from "@/lib/utils";

/**
 * Selector de modo (siempre visible en el encabezado).
 * Cambiar de modo NO reinicia la consulta: solo cambia la presentación.
 */
export function ModeSwitch({ mode, onChange, compact = false }: { mode: Mode; onChange: (mode: Mode) => void; compact?: boolean }) {
  const options: Array<{ id: Mode; label: string; Icon: typeof Compass }> = [
    { id: "explorador", label: "Explorador", Icon: Compass },
    { id: "cientifico", label: "Científico", Icon: ChartLine },
  ];
  return (
    <div role="group" aria-label="Modo de experiencia" className="inline-flex gap-1 rounded-full bg-panel-2 p-1">
      {options.map(({ id, label, Icon }) => {
        const active = mode === id;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(id)}
            className={cn(
              "inline-flex min-h-10 items-center gap-2 rounded-full px-3.5 font-display text-sm transition-colors",
              active
                ? id === "explorador"
                  ? "border border-linea bg-superficie font-bold text-bosque"
                  : "border border-hielo bg-hielo font-bold text-hielo-tinta"
                : "border border-transparent font-semibold text-texto-suave hover:text-texto",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            <span className={cn(compact && "sr-only sm:not-sr-only")}>{label}</span>
          </button>
        );
      })}
    </div>
  );
}
