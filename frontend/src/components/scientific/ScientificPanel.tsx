import { Download, ExternalLink } from "lucide-react";
import { useState } from "react";

import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { LayerToggles } from "@/components/maps/LayerToggles";
import { MapLegend } from "@/components/maps/MapLegend";
import { PointReadout } from "@/components/maps/PointReadout";
import { TrendForTarget, TrendSummary } from "@/components/maps/TrendSummary";
import { RegionSelector } from "@/components/navigation/RegionSelector";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { StatusMessage } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { regionParam } from "@/context/atlasState";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLE_IDS, type VariableId } from "@/config/variables";
import { useApi } from "@/hooks/useApi";
import { useLanguage, useVariables } from "@/i18n/language";
import { capitalize, formatYm, humanYm } from "@/lib/dates";
import { formatCoord, formatNumber, formatPercent } from "@/lib/format";
import { VERDICT_TONE, formatP } from "@/lib/trendFormat";
import { cn } from "@/lib/utils";
import { api, exportUrls, type Target } from "@/services/api";
import type { LayerResponse, Stats } from "@/services/types";

function useTarget(): { target: Target; label: string } {
  const { state } = useAtlas();
  const { lang, t } = useLanguage();
  if (state.point) {
    return {
      target: { lat: state.point.lat, lon: state.point.lon },
      label: t.scientific.point(formatCoord(state.point.lat, state.point.lon, lang)),
    };
  }
  return { target: { region: regionParam(state.region) }, label: state.region ? state.region.name : t.scientific.allMexico };
}

function StatGrid({ stats, variable }: { stats: Stats; variable: VariableId }) {
  const { t } = useLanguage();
  const v = useVariables()[variable];
  const fmt = (x: number | null) => (x === null ? "—" : formatNumber(x / v.display.scale, 2));
  const rows: Array<[string, string]> = [
    [t.scientific.mean, fmt(stats.mean)],
    [t.scientific.median, fmt(stats.median)],
    [t.scientific.min, fmt(stats.min)],
    [t.scientific.max, fmt(stats.max)],
    [t.scientific.std, fmt(stats.std)],
    [t.scientific.coverage, formatPercent(stats.coverage)],
  ];
  return (
    <dl className="grid grid-cols-2 gap-px overflow-hidden rounded-xl bg-borde sm:grid-cols-3">
      {rows.map(([label, value]) => (
        <div key={label} className="bg-panel p-3">
          <dt className="text-xs text-texto-suave">{label}</dt>
          <dd className="mt-0.5 font-display text-lg font-medium font-semicondensada cifras">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

function StatisticsSection({ theme }: { theme: "claro" | "oscuro" }) {
  const { state } = useAtlas();
  const { lang, t } = useLanguage();
  const variables = useVariables();
  const region = regionParam(state.region);
  const result = useApi(
    (signal) => api.statistics(state.variable, state.date.year, state.date.month, region, signal),
    [state.variable, state.date.year, state.date.month, region],
  );
  const v = variables[state.variable];
  return (
    <div className="flex flex-col gap-4 p-4">
      <RegionSelector />
      <h3 className="text-base font-bold">
        {v.name}, {humanYm(state.date, lang)} — {state.region?.name ?? t.scientific.allMexico}
        <span className="ml-1 font-normal text-texto-suave">({v.display.displayUnit})</span>
      </h3>
      {result.status === "loading" && !result.data && <StatusMessage kind="loading" title={t.scientific.computingStats} />}
      {result.status === "error" && <StatusMessage kind="error" title={t.scientific.noStats}>{result.error.message}</StatusMessage>}
      {result.data && (
        <>
          <StatGrid stats={result.data.stats} variable={state.variable} />
          <p className="text-xs leading-relaxed text-texto-suave">
            {t.scientific.cellsWithData(result.data.stats.n_valid, result.data.stats.n_cells)} {result.data.method}
          </p>
          {result.data.extremes.max && result.data.extremes.min && (
            <p className="text-sm">
              {t.scientific.extremes(
                formatCoord(result.data.extremes.max.lat, result.data.extremes.max.lon, lang),
                formatCoord(result.data.extremes.min.lat, result.data.extremes.min.lon, lang),
              )}
            </p>
          )}
        </>
      )}
      {state.mapView === "tendencia" ? <TrendForTarget theme={theme} detailed /> : <PointReadout />}
    </div>
  );
}

function SeriesSection({ theme }: { theme: "claro" | "oscuro" }) {
  const { state } = useAtlas();
  const { t } = useLanguage();
  const variables = useVariables();
  const { target, label } = useTarget();
  const [second, setSecond] = useState<VariableId | "">("");
  const key = JSON.stringify(target);
  const series = useApi((signal) => api.timeseries(state.variable, target, {}, signal), [state.variable, key]);
  const secondSeries = useApi(
    second ? (signal) => api.timeseries(second, target, {}, signal) : null,
    [second, key],
  );
  const correlation = useApi(
    second ? (signal) => api.correlation(state.variable, second, target, signal) : null,
    [second, state.variable, key],
  );
  const v = variables[state.variable];
  const trend = series.data?.trend;
  const intro = t.scientific.seriesIntro(label);
  return (
    <div className="flex flex-col gap-4 p-4">
      <p className="text-sm text-texto-suave">
        {intro.before}
        <strong className="text-texto">{v.name}</strong>
        {intro.after}
      </p>
      {series.status === "loading" && !series.data && <StatusMessage kind="loading" title={t.scientific.loadingSeries} />}
      {series.status === "error" && <StatusMessage kind="error">{series.error.message}</StatusMessage>}
      {series.data && (
        <TimeSeriesChart series={series.data} second={secondSeries.data} theme={theme} />
      )}
      {trend && (
        <section className="rounded-xl bg-panel p-3 text-sm" aria-label={t.scientific.annualTrendTitle}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-display font-bold">{t.scientific.annualTrendTitle}</h4>
            <Badge tone={VERDICT_TONE[trend.verdict]}>{trend.verdict_label}</Badge>
          </div>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 cifras">
            <dt className="text-texto-suave">{t.scientific.slope}</dt>
            <dd className="font-display font-semibold">
              {formatNumber(trend.slope_per_decade / v.display.scale, 2)} {v.display.displayUnit} {t.common.perDecade}
            </dd>
            <dt className="text-texto-suave">{t.scientific.ci(Math.round(trend.confidence * 100))}</dt>
            <dd>
              {formatNumber(trend.slope_ci_low_per_decade / v.display.scale, 2)} {t.common.to}{" "}
              {formatNumber(trend.slope_ci_high_per_decade / v.display.scale, 2)} {v.display.displayUnit} {t.common.perDecade}
            </dd>
            <dt className="text-texto-suave">{t.scientific.mannKendall}</dt>
            <dd>
              p = {formatP(trend.p_value)} · {trend.n_years} {t.scientific.years}
              {trend.autocorrelation_factor > 1.0001 && (
                <span className="text-texto-suave">
                  {" "}
                  ({t.scientific.uncorrected}: p = {formatP(trend.p_value_uncorrected)})
                </span>
              )}
            </dd>
          </dl>
          <p className="mt-2 leading-relaxed">{trend.interpretation}</p>
          <p className="mt-1 text-xs text-texto-suave">{trend.method}.</p>
        </section>
      )}
      {series.data?.trend_monthly && (
        <TrendSummary variable={state.variable} trend={series.data.trend_monthly} theme={theme} detailed />
      )}
      {series.data && !trend && (
        <p className="text-xs text-texto-suave">
          {t.scientific.trendNeedsYears}
        </p>
      )}
      <Select
        label={t.scientific.compareWith}
        value={second}
        onChange={(e) => setSecond(e.target.value as VariableId | "")}
        options={[
          { value: "", label: t.scientific.none },
          ...VARIABLE_IDS.filter((id) => id !== state.variable).map((id) => ({ value: id, label: variables[id].name })),
        ]}
      />
      {correlation.status === "error" && <StatusMessage kind="error">{correlation.error.message}</StatusMessage>}
      {correlation.data && (
        <section className="rounded-xl bg-panel p-3 text-sm">
          <h4 className="font-display font-bold">{t.scientific.correlationTitle}</h4>
          <p className="mt-1 font-display font-semicondensada cifras">
            r = {correlation.data.r === null ? "—" : correlation.data.r.toFixed(2)}
            {correlation.data.ci_low !== null && correlation.data.ci_high !== null && (
              <>
                {" "}
                ({t.scientific.ci(Math.round(correlation.data.confidence * 100))}: {correlation.data.ci_low.toFixed(2)}{" "}
                {t.common.to}{" "}
                {correlation.data.ci_high.toFixed(2)})
              </>
            )}{" "}
            · p = {correlation.data.p_value === null ? "—" : formatP(correlation.data.p_value)}
          </p>
          <p className="mt-1 text-xs text-texto-suave cifras">
            {correlation.data.n} {t.scientific.months}
            {correlation.data.n_effective !== null && t.scientific.independent(Math.round(correlation.data.n_effective))}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-texto-suave">
            {correlation.data.start} {t.common.to} {correlation.data.end}. {correlation.data.method} {correlation.data.note}
          </p>
        </section>
      )}
    </div>
  );
}

function CompareSection() {
  const { state, dispatch } = useAtlas();
  const { lang, t } = useLanguage();
  const variables = useVariables();
  const region = regionParam(state.region);
  const a = formatYm(state.compare.date);
  const b = formatYm(state.date);
  const result = useApi(
    state.compare.enabled ? (signal) => api.compare(state.variable, a, b, region, signal) : null,
    [state.compare.enabled, state.variable, a, b, region],
  );
  const v = variables[state.variable];
  if (!state.compare.enabled) {
    return (
      <div className="flex flex-col gap-3 p-4">
        <p className="text-sm text-texto-suave">
          {t.scientific.compareHint}
        </p>
        <button
          type="button"
          className={buttonVariants({ variant: "primary", size: "md" })}
          onClick={() => dispatch({ type: "toggleCompare" })}
        >
          {t.scientific.enableCompare}
        </button>
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-4 p-4">
      <RegionSelector />
      {result.status === "error" && <StatusMessage kind="error">{result.error.message}</StatusMessage>}
      {result.data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div>
              <h4 className="mb-2 font-display text-sm font-bold">A · {capitalize(humanYm(result.data.a.date, lang))}</h4>
              <StatGrid stats={result.data.a.stats} variable={state.variable} />
            </div>
            <div>
              <h4 className="mb-2 font-display text-sm font-bold">B · {capitalize(humanYm(result.data.b.date, lang))}</h4>
              <StatGrid stats={result.data.b.stats} variable={state.variable} />
            </div>
          </div>
          <p className="text-sm">
            {t.scientific.meanDifference}{" "}
            <strong className="font-display cifras">
              {result.data.difference_mean === null
                ? "—"
                : `${formatNumber(result.data.difference_mean / v.display.scale, 2)} ${v.display.displayUnit}`}
            </strong>
            {result.data.percent_change !== null && ` (${formatNumber(result.data.percent_change, 1)} %)`}.{" "}
            {t.scientific.increasedIn(formatPercent(result.data.cells_increase_fraction))}
          </p>
          <p className="text-xs text-texto-suave">{result.data.method}</p>
        </>
      )}
    </div>
  );
}

function MetadataSection({ layer }: { layer: LayerResponse | null }) {
  const { state } = useAtlas();
  const { lang, t } = useLanguage();
  const meta = useApi((signal) => api.metadata(state.variable, signal), [state.variable]);
  if (meta.status === "error") return <StatusMessage kind="error" className="m-4">{meta.error.message}</StatusMessage>;
  if (!meta.data) return <StatusMessage kind="loading" className="m-4" title={t.scientific.loadingMetadata} />;
  const info = meta.data.variable;
  const product = info.product as Record<string, string>;
  const rows: Array<[string, string]> = [
    [t.scientific.product, `${product.short_name} ${t.scientific.version} ${product.version}`],
    [t.scientific.title, product.title ?? ""],
    [t.scientific.missionInstrument, `${product.mission}; ${product.instrument}`],
    [t.scientific.provider, product.provider ?? ""],
    ["DOI", product.doi ?? ""],
    [t.scientific.dataType, info.data_type],
    [t.scientific.spatialResolution, String(info.spatial.native_resolution)],
    [t.scientific.temporalResolution, String(info.temporal.native_resolution)],
    [
      t.scientific.available,
      `${humanYm(info.availability.start, lang)} ${t.common.to} ${humanYm(info.availability.end, lang)}`,
    ],
    [t.common.unit, `${info.unit} (${info.unit_long})`],
  ];
  return (
    <div className="flex flex-col gap-4 p-4">
      <dl className="grid grid-cols-[minmax(110px,auto)_1fr] text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="contents">
            <dt className="border-b border-borde py-2 pr-3 text-texto-suave">{label}</dt>
            <dd className="border-b border-borde py-2 font-display font-semicondensada break-words">{value}</dd>
          </div>
        ))}
      </dl>
      {layer && (
        <section className="flex flex-col gap-2">
          <h4 className="font-display font-bold">{t.scientific.layerQuality}</h4>
          <div className="flex flex-wrap gap-2">
            {layer.quality.flags.map((flag) => (
              <Badge key={flag} tone={flag === "demo" ? "demo" : "warning"}>
                {flag === "demo" ? t.scientific.simulatedData : flag === "deriva_orbital_terra" ? t.common.terraDrift : flag}
              </Badge>
            ))}
            <Badge tone="accent">{t.scientific.coverageBadge(formatPercent(layer.quality.coverage))}</Badge>
          </div>
          {layer.quality.notes.map((note) => (
            <p key={note} className="text-sm text-texto-suave">{note}</p>
          ))}
        </section>
      )}
      <section className="flex flex-col gap-2">
        <h4 className="font-display font-bold">{t.scientific.processing}</h4>
        {Object.entries(info.processing).map(([key, value]) => (
          <p key={key} className="text-sm leading-relaxed text-texto-suave">{value}</p>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <h4 className="font-display font-bold">{t.scientific.caveats}</h4>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm leading-relaxed">
          {info.caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-1">
        <h4 className="font-display font-bold">{t.scientific.sources(meta.data.audit_date)}</h4>
        {info.sources.map((s) => (
          <a key={s.url} href={s.url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-sm">
            {s.label} <ExternalLink aria-hidden="true" className="size-3.5" />
          </a>
        ))}
      </section>
    </div>
  );
}

function ExportSection({ mode }: { mode: "demo" | "real" | null }) {
  const { state } = useAtlas();
  const { lang, t } = useLanguage();
  const { target, label } = useTarget();
  const region = regionParam(state.region);
  const links = [
    { label: t.scientific.exportSeries(label), href: exportUrls.timeseriesCsv(state.variable, target), enabled: true },
    {
      label: t.scientific.exportStats(humanYm(state.date, lang)),
      href: exportUrls.statisticsCsv(state.variable, state.date.year, state.date.month, region),
      enabled: true,
    },
    {
      label: t.scientific.exportRaster(humanYm(state.date, lang)),
      href: exportUrls.raster(state.variable, state.date.year, state.date.month),
      enabled: mode === "real",
    },
  ];
  return (
    <div className="flex flex-col gap-3 p-4">
      {mode === "demo" && (
        <StatusMessage kind="info" title={t.scientific.exportDemoTitle}>
          {t.scientific.exportDemoText}
        </StatusMessage>
      )}
      {links.map((link) =>
        link.enabled ? (
          <a key={link.label} href={link.href} download className={cn(buttonVariants({ variant: "secondary" }), "justify-start no-underline")}>
            <Download aria-hidden="true" />
            {link.label}
          </a>
        ) : (
          <span key={link.label} aria-disabled="true" className={cn(buttonVariants({ variant: "secondary" }), "justify-start opacity-45")}>
            <Download aria-hidden="true" />
            {link.label}
          </span>
        ),
      )}
      <p className="text-xs text-texto-suave">
        {t.scientific.exportHint}
      </p>
    </div>
  );
}

/** Panel del modo Científico. */
export function ScientificPanel({ layer, theme, mode }: { layer: LayerResponse | null; theme: "claro" | "oscuro"; mode: "demo" | "real" | null }) {
  const [tab, setTab] = useState("estadisticas");
  const { state } = useAtlas();
  const { t } = useLanguage();
  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-3 border-b border-borde p-4">
        <MapLegend variable={state.variable} mode="cientifico" />
      </div>
      <Tabs
        label={t.scientific.tabsLabel}
        value={tab}
        onChange={setTab}
        className="min-h-0 flex-1"
        items={[
          { id: "estadisticas", label: t.scientific.statistics, content: <StatisticsSection theme={theme} /> },
          { id: "series", label: t.scientific.series, content: <SeriesSection theme={theme} /> },
          { id: "comparar", label: t.scientific.compare, content: <CompareSection /> },
          { id: "metadatos", label: t.scientific.metadata, content: <MetadataSection layer={layer} /> },
          { id: "exportar", label: t.scientific.export, content: <ExportSection mode={mode} /> },
          { id: "capas", label: t.scientific.layers, content: <div className="p-4"><LayerToggles /></div> },
        ]}
      />
    </div>
  );
}
