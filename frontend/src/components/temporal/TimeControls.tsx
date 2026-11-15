import { ChevronLeft, ChevronRight, GitCompareArrows, Pause, Play } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES } from "@/config/variables";
import { usePlayback } from "@/hooks/usePlayback";
import { MONTHS_ES, capitalize, inRange, yearsOf, type YearMonth } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** Selectores de año y mes que solo permiten fechas con datos de la variable. */
function DatePicker({
  value,
  onChange,
  label,
}: {
  value: YearMonth;
  onChange: (date: YearMonth) => void;
  label: string;
}) {
  const { state } = useAtlas();
  const availability = VARIABLES[state.variable].availability;
  const years = yearsOf({ start: "2000-01", end: "2025-12" });
  return (
    <div className="flex gap-2">
      <Select
        label={`Mes ${label}`}
        hideLabel
        value={String(value.month)}
        onChange={(e) => onChange({ year: value.year, month: Number(e.target.value) })}
        options={MONTHS_ES.map((name, i) => ({
          value: String(i + 1),
          label: capitalize(name),
          disabled: !inRange({ year: value.year, month: i + 1 }, availability),
        }))}
        className="w-36"
      />
      <Select
        label={`Año ${label}`}
        hideLabel
        value={String(value.year)}
        onChange={(e) => onChange({ year: Number(e.target.value), month: value.month })}
        options={years.map((y) => ({
          value: String(y),
          label: String(y),
          disabled: !inRange({ year: y, month: 12 }, availability) && !inRange({ year: y, month: 1 }, availability),
        }))}
        className="w-26"
      />
    </div>
  );
}

/**
 * Controles temporales: mes y año, anterior/siguiente, reproducción animada y
 * comparación de dos fechas. Respetan la disponibilidad real de cada variable.
 */
export function TimeControls() {
  const { state, dispatch } = useAtlas();
  const { playing, toggle } = usePlayback();

  return (
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1">
        <Button size="icon" variant="ghost" aria-label="Mes anterior" onClick={() => dispatch({ type: "stepMonth", step: -1 })}>
          <ChevronLeft aria-hidden="true" />
        </Button>
        <DatePicker value={state.date} label="consultado" onChange={(date) => dispatch({ type: "setDate", date })} />
        <Button size="icon" variant="ghost" aria-label="Mes siguiente" onClick={() => dispatch({ type: "stepMonth", step: 1 })}>
          <ChevronRight aria-hidden="true" />
        </Button>
      </div>
      <Button
        variant="primary"
        size="icon"
        aria-label={playing ? "Pausar la animación" : "Reproducir la animación mes a mes"}
        aria-pressed={playing}
        onClick={toggle}
      >
        {playing ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
      </Button>
      <Button
        variant="secondary"
        size="md"
        aria-pressed={state.compare.enabled}
        onClick={() => dispatch({ type: "toggleCompare" })}
        className={cn(state.compare.enabled && "border-acento bg-acento-suave text-texto")}
      >
        <GitCompareArrows aria-hidden="true" />
        Comparar
      </Button>
      {state.compare.enabled && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-texto-suave">con</span>
          <DatePicker
            value={state.compare.date}
            label="de comparación"
            onChange={(date) => dispatch({ type: "setCompareDate", date })}
          />
        </div>
      )}
    </div>
  );
}
