import { CloudRain, Thermometer } from "lucide-react";

import type { VariableId } from "@/config/variables";

/**
 * Ícono de cada variable. Precipitación y temperatura vienen de Lucide; NO₂
 * (molécula angular de un nitrógeno y dos oxígenos) y evapotranspiración (brote
 * con vapor) están dibujados a la medida con el mismo trazo de 2 px.
 */
export function VariableIcon({ variable, size = 20 }: { variable: VariableId; size?: number }) {
  const common = {
    width: size,
    height: size,
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 2,
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    "aria-hidden": true,
  };
  switch (variable) {
    case "precipitation":
      return <CloudRain size={size} aria-hidden="true" />;
    case "temperature":
      return <Thermometer size={size} aria-hidden="true" />;
    case "no2":
      return (
        <svg {...common}>
          <circle cx="12" cy="9" r="3.2" />
          <circle cx="5.5" cy="16.5" r="2.6" />
          <circle cx="18.5" cy="16.5" r="2.6" />
          <path d="M9.9 11.4l-2.6 3.2" />
          <path d="M14.1 11.4l2.6 3.2" />
        </svg>
      );
    case "evapotranspiration":
      return (
        <svg {...common}>
          <path d="M12 21v-8" />
          <path d="M12 13c-4 0-6-2-6-5 3.5 0 6 1.5 6 5z" />
          <path d="M12 15c0-3.5 2.5-5 6-5 0 3-2 5-6 5z" />
          <path d="M8 2.5c.8.8.8 1.7 0 2.5" />
          <path d="M15.5 2.5c.8.8.8 1.7 0 2.5" />
        </svg>
      );
  }
}
