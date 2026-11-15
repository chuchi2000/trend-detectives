import type { PlotData } from "plotly.js-dist-min";
import { useMemo } from "react";

import { PlotlyChart } from "@/components/charts/PlotlyChart";
import type { VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";
import type { TrendMonthly } from "@/services/types";

/**
 * Anomalías mensuales (cada mes menos el promedio de ese mes del año) con la
 * recta de tendencia punteada y = ȳ + b·(t − t̄). Los meses sin dato quedan como huecos.
 */
export function AnomalyChart({
  variable,
  trend,
  theme,
  height = 240,
}: {
  variable: VariableId;
  trend: TrendMonthly;
  theme: "claro" | "oscuro";
  height?: number;
}) {
  const { t } = useLanguage();
  const v = useVariables()[variable];
  const data = useMemo(() => {
    const x = trend.dates.map((d) => `${d}-15`);
    const up = trend.slope_per_decade >= 0;
    const traces: PlotData[] = [
      {
        type: "bar",
        name: t.charts.monthlyAnomaly,
        x,
        y: trend.anomalies,
        marker: {
          color: trend.anomalies.map((a) => (a === null ? "rgba(0,0,0,0)" : a >= 0 ? "#D6604D" : "#4393C3")),
        },
        hovertemplate: `%{x|%b %Y}: %{y:+.2f} ${v.display.displayUnit}<extra></extra>`,
      } as PlotData,
      {
        type: "scatter",
        mode: "lines",
        name: t.charts.trendLine(`${up ? "+" : ""}${trend.slope_per_decade.toFixed(2)} ${trend.unit}`),
        x,
        y: trend.trend_line,
        line: { color: theme === "oscuro" ? "#E6EEF0" : "#10302A", width: 2.2, dash: "dash" },
        hoverinfo: "skip",
      } as PlotData,
    ];
    return traces;
  }, [trend, theme, v.display.displayUnit, t]);

  const layout = useMemo(
    () => ({ yaxis: { title: { text: t.charts.anomalyAxis(v.display.displayUnit) } }, bargap: 0 }),
    [v.display.displayUnit, t],
  );

  return (
    <PlotlyChart
      data={data}
      layout={layout as never}
      theme={theme}
      height={height}
      title={t.charts.anomalyTitle(v.name)}
    />
  );
}
