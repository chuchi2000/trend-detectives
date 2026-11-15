import type { Layout, PlotData } from "plotly.js-dist-min";
import { useEffect, useRef, useState } from "react";

import { StatusMessage } from "@/components/ui/status";

/**
 * Envoltura de Plotly.js. La librería pesa varios MB, así que se carga solo
 * cuando se muestra la primera gráfica (import dinámico). La barra de Plotly
 * incluye "Descargar como PNG".
 */
export function PlotlyChart({
  data,
  layout,
  theme,
  title,
  height = 300,
}: {
  data: PlotData[];
  layout?: Layout;
  theme: "claro" | "oscuro";
  title: string;
  height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const el = ref.current;
    if (!el) return;
    const ink = theme === "oscuro" ? "#E6EEF0" : "#10302A";
    const soft = theme === "oscuro" ? "#9FB1B8" : "#4A625C";
    const grid = theme === "oscuro" ? "#3A4A53" : "#DCE5E1";
    import("plotly.js-dist-min")
      .then((module) => {
        if (cancelled) return;
        const Plotly = module.default ?? module;
        const base: Record<string, unknown> = {
            height,
            margin: { l: 56, r: 56, t: 16, b: 40 },
            paper_bgcolor: "rgba(0,0,0,0)",
            plot_bgcolor: "rgba(0,0,0,0)",
            font: { family: "Archivo, system-ui, sans-serif", size: 12, color: soft },
            xaxis: { gridcolor: grid, linecolor: grid, color: soft },
            yaxis: { gridcolor: grid, zerolinecolor: grid, color: soft },
            legend: { orientation: "h", y: -0.2, font: { color: ink } },
            hoverlabel: { font: { family: "Archivo, system-ui, sans-serif" } },
        };
        // Mezcla superficial por eje: el diseño propio se conserva y la gráfica agrega títulos.
        for (const [key, value] of Object.entries(layout ?? {})) {
          const current = base[key];
          base[key] =
            current && typeof current === "object" && value && typeof value === "object"
              ? { ...(current as object), ...(value as object) }
              : value;
        }
        void Plotly.react(el, data, base, { displaylogo: false, responsive: true, modeBarButtonsToRemove: ["lasso2d", "select2d"] },
        );
      })
      .catch(() => setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [data, layout, theme, height]);

  useEffect(() => {
    const el = ref.current;
    return () => {
      if (el) import("plotly.js-dist-min").then((m) => (m.default ?? m).purge(el)).catch(() => undefined);
    };
  }, []);

  if (failed) return <StatusMessage kind="error">No se pudo cargar la librería de gráficas.</StatusMessage>;
  return <div ref={ref} role="img" aria-label={title} style={{ minHeight: height }} className="w-full" />;
}
