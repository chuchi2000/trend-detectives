import type { PlotData } from "plotly.js-dist-min";
import { useMemo } from "react";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import type { VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";
import type { TimeSeriesResponse } from "@/services/types";

/**
 * Serie mensual de una variable, con la línea de tendencia (Theil–Sen sobre
 * promedios anuales) y, opcionalmente, una segunda variable en otro eje.
 * Los meses sin dato quedan como huecos: nunca se rellenan con cero.
 */
export function TimeSeriesChart({
  series,
  second,
  theme,
  showTrend = true,
}: {
  series: TimeSeriesResponse;
  second?: TimeSeriesResponse | null;
  theme: "claro" | "oscuro";
  showTrend?: boolean;
}) {
  const { t } = useLanguage();
  const variables = useVariables();
  const data = useMemo(() => {
    const v = variables[series.variable];
    const scale = v.display.scale;
    const toDisplay = (value: number | null) => (value === null ? null : value / scale);
    const traces: PlotData[] = [
      {
        type: "scatter",
        mode: "lines+markers",
        name: v.shortLabel,
        x: series.points.map((p) => `${p.date}-15`),
        y: series.points.map((p) => toDisplay(p.value)),
        line: { color: v.display.identityColor, width: 1.8 },
        marker: { color: v.display.identityColor, size: 3 },
        connectgaps: false,
        hovertemplate: `%{x|%b %Y}: %{y:.2f} ${v.display.displayUnit}<extra></extra>`,
      },
    ];
    if (showTrend && series.trend) {
      const annual = series.trend;
      const slope = annual.slope_per_decade / 10;
      const first = annual.years[0] ?? 0;
      const last = annual.years[annual.years.length - 1] ?? 0;
      traces.push({
        type: "scatter",
        mode: "lines",
        name: t.charts.annualTrend,
        x: [`${first}-07-01`, `${last}-07-01`],
        y: [toDisplay(annual.intercept + slope * first), toDisplay(annual.intercept + slope * last)],
        line: { color: theme === "oscuro" ? "#E6EEF0" : "#10302A", width: 2, dash: "dash" },
      });
    }
    if (second) {
      const w = variables[second.variable as VariableId];
      traces.push({
        type: "scatter",
        mode: "lines",
        name: w.shortLabel,
        x: second.points.map((p) => `${p.date}-15`),
        y: second.points.map((p) => (p.value === null ? null : p.value / w.display.scale)),
        yaxis: "y2",
        line: { color: w.display.identityColor, width: 1.5 },
        connectgaps: false,
      });
    }
    return traces;
  }, [series, second, showTrend, theme, variables, t]);

  const layout = useMemo(() => {
    const v = variables[series.variable];
    const base: Record<string, unknown> = {
      yaxis: { title: { text: v.display.displayUnit } },
    };
    if (second) {
      const w = variables[second.variable as VariableId];
      base.yaxis2 = { title: { text: w.display.displayUnit }, overlaying: "y", side: "right", showgrid: false };
    }
    return base;
  }, [series.variable, second, variables]);

  return (
    <PlotlyChart
      data={data}
      layout={layout}
      theme={theme}
      title={t.charts.seriesTitle(variables[series.variable].name)}
    />
  );
}
