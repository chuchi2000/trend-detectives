import { HelpCircle, Lightbulb, Search } from "lucide-react";
import { useState } from "react";

import { VariableIcon } from "@/components/icons/VariableIcon";
import { LayerToggles } from "@/components/maps/LayerToggles";
import { MapLegend } from "@/components/maps/MapLegend";
import { PointReadout } from "@/components/maps/PointReadout";
import { Tabs } from "@/components/ui/tabs";
import { EDUCATIONAL } from "@/content/educational";
import { GLOSSARY } from "@/content/glossary";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES } from "@/config/variables";
import { useApi } from "@/hooks/useApi";
import { capitalize, humanYm } from "@/lib/dates";
import { formatNumber } from "@/lib/format";
import { api } from "@/services/api";

function Observe() {
  const { state } = useAtlas();
  const v = VARIABLES[state.variable];
  const content = EDUCATIONAL[state.variable];
  return (
    <div className="flex flex-col gap-5 p-4">
      <section>
        <h3 className="flex items-center gap-2 text-lg font-bold">
          <span className="text-acento">
            <VariableIcon variable={state.variable} />
          </span>
          ¿Qué estamos observando?
        </h3>
        <p className="mt-2 text-[17px] leading-relaxed">{content.whatWeSee}</p>
        <p className="mt-1 text-sm text-texto-suave">
          {capitalize(humanYm(state.date))}. Fuente: {v.product.shortName}, de {v.product.provider}.
        </p>
      </section>
      <section className="flex flex-col gap-3">
        <h3 className="text-lg font-bold">¿Cómo interpretar este mapa?</h3>
        <MapLegend variable={state.variable} mode="explorador" />
        <p className="text-[15px] leading-relaxed text-texto-suave">{content.howToRead}</p>
      </section>
      <PointReadout />
      <CompareSummary />
      <LayerToggles />
    </div>
  );
}

/** Explicación sencilla de la comparación entre dos fechas. */
function CompareSummary() {
  const { state } = useAtlas();
  const { variable, date, compare } = state;
  const result = useApi(
    compare.enabled
      ? (signal) =>
          api.compare(
            variable,
            `${compare.date.year}-${String(compare.date.month).padStart(2, "0")}`,
            `${date.year}-${String(date.month).padStart(2, "0")}`,
            "nacional",
            signal,
          )
      : null,
    [compare.enabled, compare.date.year, compare.date.month, date.year, date.month, variable],
  );
  if (!compare.enabled || result.status !== "success") return null;
  const v = VARIABLES[variable];
  const diff = result.data.difference_mean;
  const scale = v.display.scale;
  return (
    <section className="rounded-2xl border-[1.5px] border-acento p-4">
      <h3 className="font-bold text-acento">Comparación de dos meses</h3>
      <p className="mt-1 text-[15px] leading-relaxed">
        En promedio para todo el país, {humanYm(date)} tuvo{" "}
        <strong>
          {diff === null ? "—" : `${formatNumber(Math.abs(diff) / scale)} ${v.display.displayUnit} ${diff >= 0 ? "más" : "menos"}`}
        </strong>{" "}
        que {humanYm(compare.date)}.
      </p>
    </section>
  );
}

function Learn() {
  const { state } = useAtlas();
  const content = EDUCATIONAL[state.variable];
  return (
    <div className="flex flex-col gap-4 p-4">
      {content.facts.map((fact) => (
        <article key={fact.text} className="flex flex-col gap-2 rounded-2xl bg-sol-claro p-4 text-tinta">
          <h3 className="flex items-center gap-2 font-bold">
            <span className="grid size-8 place-items-center rounded-lg bg-sol">
              <Lightbulb aria-hidden="true" className="size-4.5" />
            </span>
            ¿Sabías que…?
          </h3>
          <p className="text-[16px] leading-relaxed">{fact.text}</p>
          <a href={fact.source.url} target="_blank" rel="noreferrer" className="text-sm text-oceano">
            Fuente: {fact.source.label}
          </a>
        </article>
      ))}
      <section className="flex flex-col gap-2 rounded-2xl border-[1.5px] border-acento p-4">
        <h3 className="flex items-center gap-2 font-bold text-acento">
          <HelpCircle aria-hidden="true" className="size-5" />
          Preguntas para aprender
        </h3>
        <ol className="flex list-decimal flex-col gap-2 pl-5 text-[16px] leading-relaxed">
          {content.questions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ol>
        <p className="text-sm text-texto-suave">Usa la barra cronológica y el botón de reproducir para explorar.</p>
      </section>
    </div>
  );
}

function Glossary() {
  const [query, setQuery] = useState("");
  const normalized = query.trim().toLowerCase();
  const terms = GLOSSARY.filter((t) => !normalized || `${t.term} ${t.definition}`.toLowerCase().includes(normalized));
  return (
    <div className="flex flex-col gap-3 p-4" id="glosario">
      <label className="relative block">
        <span className="sr-only">Buscar en el glosario</span>
        <Search aria-hidden="true" className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-texto-suave" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Buscar un término"
          className="min-h-11 w-full rounded-xl border-[1.5px] border-borde-fuerte bg-panel pr-3 pl-9 text-[15px]"
        />
      </label>
      <dl className="flex flex-col gap-3">
        {terms.map((t) => (
          <div key={t.term} className="rounded-xl bg-panel p-3">
            <dt className="font-display font-bold">{t.term}</dt>
            <dd className="mt-1 text-[15px] leading-relaxed text-texto-suave">{t.definition}</dd>
          </div>
        ))}
        {terms.length === 0 && <p className="text-sm text-texto-suave">No hay términos que coincidan con la búsqueda.</p>}
      </dl>
    </div>
  );
}

/** Panel del modo Explorador: observar, aprender y glosario. */
export function ExplorerPanel({ initialTab = "observar" }: { initialTab?: string }) {
  const [tab, setTab] = useState(initialTab);
  return (
    <Tabs
      label="Contenido del modo Explorador"
      value={tab}
      onChange={setTab}
      className="h-full"
      items={[
        { id: "observar", label: "Observar", content: <Observe /> },
        { id: "aprender", label: "Aprender", content: <Learn /> },
        { id: "glosario", label: "Glosario", content: <Glossary /> },
      ]}
    />
  );
}
