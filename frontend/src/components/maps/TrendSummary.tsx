import { MapPin, Minus, TrendingDown, TrendingUp, X } from "lucide-react";

import { AnomalyChart } from "@/components/charts/AnomalyChart";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status";
import type { VariableId } from "@/config/variables";
import { regionParam } from "@/context/atlasState";
import { useAtlas } from "@/context/AtlasStateContext";
import { useApi } from "@/hooks/useApi";
import { useLanguage } from "@/i18n/language";
import { formatCoord, formatNumber } from "@/lib/format";
import { api } from "@/services/api";
import { VERDICT_TONE, formatP } from "@/lib/trendFormat";
import type { TrendMonthly } from "@/services/types";

/**
 * Resultado del análisis mensual de tendencia de un punto o región:
 * frase sencilla + veredicto + gráfica de anomalías y, en modo Científico,
 * todas las cifras (pendiente, IC 95 %, Sen, %, p de Mann–Kendall y de la t, r₁, n_eff).
 */
export function TrendSummary({
  variable,
  trend,
  theme,
  detailed,
}: {
  variable: VariableId;
  trend: TrendMonthly;
  theme: "claro" | "oscuro";
  detailed: boolean;
}) {
  const { t } = useLanguage();
  const Icon = trend.verdict === "variabilidad" ? Minus : trend.slope_per_decade > 0 ? TrendingUp : TrendingDown;
  const u = trend.unit;
  const rows: Array<[string, string]> = [
    [t.trend.olsSlope, `${formatNumber(trend.slope_per_decade, 3)} ${u}`],
    [t.trend.ci95, `${formatNumber(trend.ci95[0], 3)} ${t.common.to} ${formatNumber(trend.ci95[1], 3)} ${u}`],
    [t.trend.senSlope, `${formatNumber(trend.sen_slope_per_decade, 3)} ${u}`],
    [
      t.trend.relativeChange,
      trend.pct_change_per_decade === null
        ? t.trend.relativeNone
        : t.trend.percentPerDecade(formatNumber(trend.pct_change_per_decade, 1)),
    ],
    [t.trend.mannKendall, `p = ${formatP(trend.p_value)}`],
    [t.trend.tTest, `p = ${formatP(trend.t_test_p_value)}`],
    [t.trend.lag1, formatNumber(trend.lag1_autocorrelation, 2)],
    [
      t.trend.effectiveMonths,
      t.trend.effectiveValue(formatNumber(trend.effective_months, 0), trend.months, trend.start, trend.end),
    ],
  ];
  return (
    <section className="flex flex-col gap-2 rounded-2xl border border-borde bg-panel p-4 text-sm" aria-label={t.trend.sectionAria}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h4 className="flex items-center gap-2 font-display font-bold">
          <Icon aria-hidden="true" className="size-4.5 text-acento" />
          {t.trend.title(trend.start.slice(0, 4), trend.end.slice(0, 4))}
        </h4>
        <Badge tone={VERDICT_TONE[trend.verdict]}>{trend.verdict_label}</Badge>
      </div>
      <p className="text-[15px] leading-relaxed text-texto">{trend.sentence}</p>
      {trend.notes.map((note) => (
        <StatusMessage key={note} kind="info">
          {note}
        </StatusMessage>
      ))}
      <AnomalyChart variable={variable} trend={trend} theme={theme} height={detailed ? 240 : 200} />
      {detailed ? (
        <>
          <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 cifras">
            {rows.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-texto-suave">{label}</dt>
                <dd className="font-display font-semicondensada">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="text-xs leading-relaxed text-texto-suave">{trend.method}</p>
        </>
      ) : (
        <p className="text-xs leading-relaxed text-texto-suave">
          {t.trend.explorerHint}
        </p>
      )}
    </section>
  );
}

/**
 * Pide la serie del punto elegido (o de la región / todo México si no hay punto)
 * y muestra su tendencia mensual. Se usa en la vista «Tendencia» del mapa.
 */
export function TrendForTarget({ theme, detailed }: { theme: "claro" | "oscuro"; detailed: boolean }) {
  const { state, dispatch } = useAtlas();
  const { lang, t } = useLanguage();
  const target = state.point
    ? { lat: state.point.lat, lon: state.point.lon }
    : { region: regionParam(state.region) };
  const where = state.point
    ? formatCoord(state.point.lat, state.point.lon, lang)
    : (state.region?.name ?? t.scientific.allMexico);
  const key = JSON.stringify(target);
  const series = useApi((signal) => api.timeseries(state.variable, target, {}, signal), [state.variable, key]);
  const trend = series.data?.variable === state.variable ? series.data.trend_monthly : null;
  return (
    <div className="flex flex-col gap-2" aria-live="polite">
      <div className="flex items-start justify-between gap-2">
        <p className="flex items-center gap-2 text-sm text-texto-suave">
          <MapPin aria-hidden="true" className="size-4 shrink-0 text-acento" />
          {state.point ? t.trend.atPoint(where) : t.trend.atRegion(where)}
        </p>
        {state.point && (
          <Button size="icon" variant="ghost" aria-label={t.common.removePoint} onClick={() => dispatch({ type: "setPoint", point: null })}>
            <X aria-hidden="true" />
          </Button>
        )}
      </div>
      {series.status === "loading" && !trend && <StatusMessage kind="loading" title={t.trend.computing} />}
      {series.status === "error" && <StatusMessage kind="error">{series.error.message}</StatusMessage>}
      {series.status === "success" && !trend && (
        <StatusMessage kind="empty" title={t.trend.noTrendTitle}>
          {t.trend.noTrendText}
        </StatusMessage>
      )}
      {trend && <TrendSummary variable={state.variable} trend={trend} theme={theme} detailed={detailed} />}
    </div>
  );
}
