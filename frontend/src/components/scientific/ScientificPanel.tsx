import { Download, ExternalLink } from "lucide-react";
import { useState } from "react";

import { TimeSeriesChart } from "@/components/charts/TimeSeriesChart";
import { LayerToggles } from "@/components/maps/LayerToggles";
import { MapLegend } from "@/components/maps/MapLegend";
import { PointReadout } from "@/components/maps/PointReadout";
import { RegionSelector } from "@/components/navigation/RegionSelector";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { StatusMessage } from "@/components/ui/status";
import { Tabs } from "@/components/ui/tabs";
import { regionParam } from "@/context/atlasState";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES, VARIABLE_IDS, type VariableId } from "@/config/variables";
import { useApi } from "@/hooks/useApi";
import { capitalize, formatYm, humanYm } from "@/lib/dates";
import { formatCoord, formatNumber, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { api, exportUrls, type Target } from "@/services/api";
import type { LayerResponse, Stats, TrendVerdict } from "@/services/types";

const VERDICT_TONE: Record<TrendVerdict, "accent" | "warning" | "neutral"> = {
  solida: "accent",
  indicio: "warning",
  variabilidad: "neutral",
};

function formatP(p: number): string {
  return p < 0.001 ? "< 0.001" : p.toFixed(3);
}

function useTarget(): { target: Target; label: string } {
  const { state } = useAtlas();
  if (state.point) {
    return { target: { lat: state.point.lat, lon: state.point.lon }, label: `punto ${formatCoord(state.point.lat, state.point.lon)}` };
  }
  return { target: { region: regionParam(state.region) }, label: state.region ? state.region.name : "todo México" };
}

function StatGrid({ stats, variable }: { stats: Stats; variable: VariableId }) {
  const v = VARIABLES[variable];
  const fmt = (x: number | null) => (x === null ? "—" : formatNumber(x / v.display.scale, 2));
  const rows: Array<[string, string]> = [
    ["Promedio", fmt(stats.mean)],
    ["Mediana", fmt(stats.median)],
    ["Mínimo", fmt(stats.min)],
    ["Máximo", fmt(stats.max)],
    ["Desv. estándar", fmt(stats.std)],
    ["Cobertura válida", formatPercent(stats.coverage)],
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

function StatisticsSection() {
  const { state } = useAtlas();
  const region = regionParam(state.region);
  const result = useApi(
    (signal) => api.statistics(state.variable, state.date.year, state.date.month, region, signal),
    [state.variable, state.date.year, state.date.month, region],
  );
  const v = VARIABLES[state.variable];
  return (
    <div className="flex flex-col gap-4 p-4">
      <RegionSelector />
      <h3 className="text-base font-bold">
        {v.name}, {humanYm(state.date)} — {state.region?.name ?? "todo México"}
        <span className="ml-1 font-normal text-texto-suave">({v.display.displayUnit})</span>
      </h3>
      {result.status === "loading" && !result.data && <StatusMessage kind="loading" title="Calculando estadísticas…" />}
      {result.status === "error" && <StatusMessage kind="error" title="Sin estadísticas">{result.error.message}</StatusMessage>}
      {result.data && (
        <>
          <StatGrid stats={result.data.stats} variable={state.variable} />
          <p className="text-xs leading-relaxed text-texto-suave">
            {result.data.stats.n_valid} de {result.data.stats.n_cells} celdas con dato. {result.data.method}
          </p>
          {result.data.extremes.max && result.data.extremes.min && (
            <p className="text-sm">
              Máximo en {formatCoord(result.data.extremes.max.lat, result.data.extremes.max.lon)}; mínimo en{" "}
              {formatCoord(result.data.extremes.min.lat, result.data.extremes.min.lon)}.
            </p>
          )}
        </>
      )}
      <PointReadout />
    </div>
  );
}

function SeriesSection({ theme }: { theme: "claro" | "oscuro" }) {
  const { state } = useAtlas();
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
  const v = VARIABLES[state.variable];
  const trend = series.data?.trend;
  return (
    <div className="flex flex-col gap-4 p-4">
      <p className="text-sm text-texto-suave">
        Serie mensual de <strong className="text-texto">{v.name}</strong> en {label}. Haz clic en el mapa para cambiar
        de punto, o quita el punto para ver la región.
      </p>
      {series.status === "loading" && !series.data && <StatusMessage kind="loading" title="Cargando la serie…" />}
      {series.status === "error" && <StatusMessage kind="error">{series.error.message}</StatusMessage>}
      {series.data && (
        <TimeSeriesChart series={series.data} second={secondSeries.data} theme={theme} />
      )}
      {trend && (
        <section className="rounded-xl bg-panel p-3 text-sm" aria-label="Tendencia">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h4 className="font-display font-bold">Tendencia</h4>
            <Badge tone={VERDICT_TONE[trend.verdict]}>{trend.verdict_label}</Badge>
          </div>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 cifras">
            <dt className="text-texto-suave">Pendiente</dt>
            <dd className="font-display font-semibold">
              {formatNumber(trend.slope_per_decade / v.display.scale, 2)} {v.display.displayUnit} por década
            </dd>
            <dt className="text-texto-suave">IC {Math.round(trend.confidence * 100)} %</dt>
            <dd>
              {formatNumber(trend.slope_ci_low_per_decade / v.display.scale, 2)} a{" "}
              {formatNumber(trend.slope_ci_high_per_decade / v.display.scale, 2)} {v.display.displayUnit} por década
            </dd>
            <dt className="text-texto-suave">Mann–Kendall</dt>
            <dd>
              p = {formatP(trend.p_value)} · {trend.n_years} años
              {trend.autocorrelation_factor > 1.0001 && (
                <span className="text-texto-suave"> (sin corregir: p = {formatP(trend.p_value_uncorrected)})</span>
              )}
            </dd>
          </dl>
          <p className="mt-2 leading-relaxed">{trend.interpretation}</p>
          <p className="mt-1 text-xs text-texto-suave">{trend.method}.</p>
        </section>
      )}
      {series.data && !trend && (
        <p className="text-xs text-texto-suave">
          La tendencia se calcula con al menos 8 años completos (9 meses válidos o más por año).
        </p>
      )}
      <Select
        label="Comparar con otra variable"
        value={second}
        onChange={(e) => setSecond(e.target.value as VariableId | "")}
        options={[
          { value: "", label: "Ninguna" },
          ...VARIABLE_IDS.filter((id) => id !== state.variable).map((id) => ({ value: id, label: VARIABLES[id].name })),
        ]}
      />
      {correlation.status === "error" && <StatusMessage kind="error">{correlation.error.message}</StatusMessage>}
      {correlation.data && (
        <section className="rounded-xl bg-panel p-3 text-sm">
          <h4 className="font-display font-bold">Correlación de anomalías mensuales</h4>
          <p className="mt-1 font-display font-semicondensada cifras">
            r = {correlation.data.r === null ? "—" : correlation.data.r.toFixed(2)}
            {correlation.data.ci_low !== null && correlation.data.ci_high !== null && (
              <>
                {" "}
                (IC {Math.round(correlation.data.confidence * 100)} %: {correlation.data.ci_low.toFixed(2)} a{" "}
                {correlation.data.ci_high.toFixed(2)})
              </>
            )}{" "}
            · p = {correlation.data.p_value === null ? "—" : formatP(correlation.data.p_value)}
          </p>
          <p className="mt-1 text-xs text-texto-suave cifras">
            {correlation.data.n} meses
            {correlation.data.n_effective !== null &&
              ` · equivalen a ≈ ${Math.round(correlation.data.n_effective)} datos independientes por la autocorrelación`}
          </p>
          <p className="mt-1 text-xs leading-relaxed text-texto-suave">
            {correlation.data.start} a {correlation.data.end}. {correlation.data.method} {correlation.data.note}
          </p>
        </section>
      )}
    </div>
  );
}

function CompareSection() {
  const { state, dispatch } = useAtlas();
  const region = regionParam(state.region);
  const a = formatYm(state.compare.date);
  const b = formatYm(state.date);
  const result = useApi(
    state.compare.enabled ? (signal) => api.compare(state.variable, a, b, region, signal) : null,
    [state.compare.enabled, state.variable, a, b, region],
  );
  const v = VARIABLES[state.variable];
  if (!state.compare.enabled) {
    return (
      <div className="flex flex-col gap-3 p-4">
        <p className="text-sm text-texto-suave">
          Activa “Comparar” en los controles de tiempo para elegir un segundo mes y ver la diferencia.
        </p>
        <button
          type="button"
          className={buttonVariants({ variant: "primary", size: "md" })}
          onClick={() => dispatch({ type: "toggleCompare" })}
        >
          Activar comparación
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
              <h4 className="mb-2 font-display text-sm font-bold">A · {capitalize(humanYm(result.data.a.date))}</h4>
              <StatGrid stats={result.data.a.stats} variable={state.variable} />
            </div>
            <div>
              <h4 className="mb-2 font-display text-sm font-bold">B · {capitalize(humanYm(result.data.b.date))}</h4>
              <StatGrid stats={result.data.b.stats} variable={state.variable} />
            </div>
          </div>
          <p className="text-sm">
            Diferencia media (B − A):{" "}
            <strong className="font-display cifras">
              {result.data.difference_mean === null
                ? "—"
                : `${formatNumber(result.data.difference_mean / v.display.scale, 2)} ${v.display.displayUnit}`}
            </strong>
            {result.data.percent_change !== null && ` (${formatNumber(result.data.percent_change, 1)} %)`}. Aumentó en{" "}
            {formatPercent(result.data.cells_increase_fraction)} de las celdas comparables.
          </p>
          <p className="text-xs text-texto-suave">{result.data.method}</p>
        </>
      )}
    </div>
  );
}

function MetadataSection({ layer }: { layer: LayerResponse | null }) {
  const { state } = useAtlas();
  const meta = useApi((signal) => api.metadata(state.variable, signal), [state.variable]);
  if (meta.status === "error") return <StatusMessage kind="error" className="m-4">{meta.error.message}</StatusMessage>;
  if (!meta.data) return <StatusMessage kind="loading" className="m-4" title="Cargando metadatos…" />;
  const info = meta.data.variable;
  const product = info.product as Record<string, string>;
  const rows: Array<[string, string]> = [
    ["Producto", `${product.short_name} versión ${product.version}`],
    ["Título", product.title ?? ""],
    ["Misión e instrumento", `${product.mission}; ${product.instrument}`],
    ["Proveedor", product.provider ?? ""],
    ["DOI", product.doi ?? ""],
    ["Tipo de dato", info.data_type],
    ["Resolución espacial", String(info.spatial.native_resolution)],
    ["Resolución temporal", String(info.temporal.native_resolution)],
    ["Disponible", `${humanYm(info.availability.start)} a ${humanYm(info.availability.end)}`],
    ["Unidad", `${info.unit} (${info.unit_long})`],
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
          <h4 className="font-display font-bold">Calidad de la capa mostrada</h4>
          <div className="flex flex-wrap gap-2">
            {layer.quality.flags.map((flag) => (
              <Badge key={flag} tone={flag === "demo" ? "demo" : "warning"}>
                {flag === "demo" ? "Datos simulados" : flag === "deriva_orbital_terra" ? "Deriva orbital de Terra" : flag}
              </Badge>
            ))}
            <Badge tone="accent">Cobertura {formatPercent(layer.quality.coverage)}</Badge>
          </div>
          {layer.quality.notes.map((note) => (
            <p key={note} className="text-sm text-texto-suave">{note}</p>
          ))}
        </section>
      )}
      <section className="flex flex-col gap-2">
        <h4 className="font-display font-bold">Procesamiento</h4>
        {Object.entries(info.processing).map(([key, value]) => (
          <p key={key} className="text-sm leading-relaxed text-texto-suave">{value}</p>
        ))}
      </section>
      <section className="flex flex-col gap-2">
        <h4 className="font-display font-bold">Advertencias</h4>
        <ul className="flex list-disc flex-col gap-1 pl-5 text-sm leading-relaxed">
          {info.caveats.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </section>
      <section className="flex flex-col gap-1">
        <h4 className="font-display font-bold">Fuentes (auditoría del {meta.data.audit_date})</h4>
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
  const { target, label } = useTarget();
  const region = regionParam(state.region);
  const links = [
    { label: `Serie de tiempo (${label}) en CSV`, href: exportUrls.timeseriesCsv(state.variable, target), enabled: true },
    {
      label: `Estadísticas de ${humanYm(state.date)} en CSV`,
      href: exportUrls.statisticsCsv(state.variable, state.date.year, state.date.month, region),
      enabled: true,
    },
    {
      label: `Mapa de ${humanYm(state.date)} en GeoTIFF (resolución nativa)`,
      href: exportUrls.raster(state.variable, state.date.year, state.date.month),
      enabled: mode === "real",
    },
  ];
  return (
    <div className="flex flex-col gap-3 p-4">
      {mode === "demo" && (
        <StatusMessage kind="info" title="Exportaciones de demostración">
          Los CSV incluyen un encabezado que indica que los valores son simulados. El GeoTIFF solo existe con datos reales.
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
        La imagen del mapa se descarga con el botón junto al mapa; cada gráfica tiene su propio botón de descarga en PNG.
      </p>
    </div>
  );
}

/** Panel del modo Científico. */
export function ScientificPanel({ layer, theme, mode }: { layer: LayerResponse | null; theme: "claro" | "oscuro"; mode: "demo" | "real" | null }) {
  const [tab, setTab] = useState("estadisticas");
  const { state } = useAtlas();
  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-col gap-3 border-b border-borde p-4">
        <MapLegend variable={state.variable} mode="cientifico" />
      </div>
      <Tabs
        label="Herramientas de análisis"
        value={tab}
        onChange={setTab}
        className="min-h-0 flex-1"
        items={[
          { id: "estadisticas", label: "Estadísticas", content: <StatisticsSection /> },
          { id: "series", label: "Series", content: <SeriesSection theme={theme} /> },
          { id: "comparar", label: "Comparar", content: <CompareSection /> },
          { id: "metadatos", label: "Metadatos", content: <MetadataSection layer={layer} /> },
          { id: "exportar", label: "Exportar", content: <ExportSection mode={mode} /> },
          { id: "capas", label: "Capas", content: <div className="p-4"><LayerToggles /></div> },
        ]}
      />
    </div>
  );
}
