import { CalendarDays, TrendingUp } from "lucide-react";

import type { MapView } from "@/context/atlasState";
import { useLanguage } from "@/i18n/language";
import { cn } from "@/lib/utils";

/** Interruptor del mapa: «Valor del mes» o «Tendencia» de todo el periodo. */
export function MapViewSwitch({
  view,
  onChange,
  trendLabel,
}: {
  view: MapView;
  onChange: (view: MapView) => void;
  trendLabel: string;
}) {
  const { t } = useLanguage();
  const options: Array<{ id: MapView; label: string; Icon: typeof TrendingUp }> = [
    { id: "valor", label: t.mapView.value, Icon: CalendarDays },
    { id: "tendencia", label: trendLabel, Icon: TrendingUp },
  ];
  return (
    <div role="group" aria-label={t.mapView.groupLabel} className="inline-flex gap-1 rounded-full bg-panel-2 p-1">
      {options.map(({ id, label, Icon }) => {
        const active = view === id;
        return (
          <button
            key={id}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(id)}
            className={cn(
              "inline-flex min-h-9 items-center gap-2 rounded-full px-3 font-display text-sm transition-colors",
              active
                ? "border border-borde-fuerte bg-panel font-bold text-texto"
                : "border border-transparent font-semibold text-texto-suave hover:text-texto",
            )}
          >
            <Icon className="size-4" aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}
