import { ArrowLeftRight, ChartLine, Compass, Pause, Play } from "lucide-react";
import { useEffect, useState } from "react";

import { LogoLockup } from "@/components/brand/Logo";
import { MosaicMap } from "@/components/brand/MosaicMap";
import { LanguageSwitch } from "@/components/navigation/LanguageSwitch";
import { VariableIcon } from "@/components/icons/VariableIcon";
import { Button } from "@/components/ui/button";
import { STUDY_PERIOD, VARIABLE_IDS, type Mode, type VariableId } from "@/config/variables";
import { useLanguage, useVariables } from "@/i18n/language";
import { humanYm, parseYm } from "@/lib/dates";
import { cn } from "@/lib/utils";

/** Posición (0–100 %) de un mes dentro del periodo de estudio 2000–2025. */
function position(ym: string, edge: "start" | "end"): number {
  const { year, month } = parseYm(ym);
  const start = parseYm(STUDY_PERIOD.start).year;
  const months = (year - start) * 12 + (month - 1) + (edge === "end" ? 1 : 0);
  return (months / ((parseYm(STUDY_PERIOD.end).year - start + 1) * 12)) * 100;
}

/**
 * Pantalla de bienvenida (propuesta aprobada): nombre, subtítulo, las dos
 * opciones de acceso, mapa-mosaico ilustrativo y cobertura real de cada producto.
 */
export function WelcomePage({ onEnter }: { onEnter: (mode: Mode) => void }) {
  const { lang, t } = useLanguage();
  const variables = useVariables();
  const [variable, setVariable] = useState<VariableId>("precipitation");
  const [auto, setAuto] = useState(() => !window.matchMedia?.("(prefers-reduced-motion: reduce)").matches);

  useEffect(() => {
    if (!auto) return;
    const timer = window.setInterval(() => {
      setVariable((current) => VARIABLE_IDS[(VARIABLE_IDS.indexOf(current) + 1) % VARIABLE_IDS.length] ?? current);
    }, 5000);
    return () => window.clearInterval(timer);
  }, [auto]);

  const v = variables[variable];
  return (
    <div data-tema="claro" className="min-h-dvh bg-papel text-tinta [container-type:inline-size]">
      <header className="mx-auto flex max-w-[1320px] flex-wrap items-center justify-between gap-3 px-5 py-5 sm:px-10">
        <LogoLockup />
        <nav aria-label={t.welcome.navLabel} className="flex flex-wrap items-center gap-6 text-[16px]">
          <a href="#fuentes" className="py-2.5">
            {t.welcome.sourcesLink}
          </a>
          <LanguageSwitch className="bg-superficie" />
        </nav>
      </header>

      <main className="mx-auto flex max-w-[1320px] flex-wrap items-start gap-x-16 gap-y-12 px-5 pt-4 pb-12 sm:px-10">
        <section aria-labelledby="titulo-atlas" className="flex min-w-0 flex-[1_1_440px] flex-col gap-7">
          <div className="flex flex-col gap-4">
            <h1
              id="titulo-atlas"
              className={cn(
                "leading-[0.96] font-extrabold tracking-[0.005em] font-expandida",
                // «ENVIRONMENTAL» es más largo que «AMBIENTAL»: en inglés el título va más chico.
                lang === "en" ? "text-[clamp(28px,2.6cqi,40px)]" : "text-[clamp(40px,5cqi,70px)]",
              )}
            >
              {t.welcome.titleLines.map((line) => (
                <span key={line} className="block">
                  {line}
                </span>
              ))}
            </h1>
            <p className="font-display text-2xl font-medium text-bosque">{t.welcome.subtitle}</p>
            <p className="max-w-[34em] text-lg leading-relaxed text-tinta-suave">
              {t.welcome.intro}
            </p>
          </div>

          <div className="flex flex-wrap gap-4">
            <button
              type="button"
              onClick={() => onEnter("explorador")}
              className="flex min-w-0 flex-[1_1_240px] flex-col gap-3 rounded-[20px] border-2 border-bosque bg-superficie p-6 text-left transition-shadow hover:shadow-[0_0_0_4px_rgba(30,156,150,0.28)]"
            >
              <span className="grid size-12 place-items-center rounded-[14px] bg-bosque-claro text-bosque">
                <Compass aria-hidden="true" className="size-6.5" />
              </span>
              <span className="font-display text-[22px] leading-tight font-bold">{t.welcome.explorerTitle}</span>
              <span className="text-[16px] leading-normal text-tinta-suave">
                {t.welcome.explorerText}
              </span>
              <span className="mt-auto inline-flex min-h-11 items-center self-start rounded-full bg-bosque px-5 font-display text-[15px] font-semibold text-white">
                {t.welcome.explorerButton}
              </span>
            </button>
            <button
              type="button"
              onClick={() => onEnter("cientifico")}
              className="flex min-w-0 flex-[1_1_240px] flex-col gap-3 rounded-[20px] border-2 border-grafito bg-grafito p-6 text-left text-niebla transition-shadow hover:shadow-[0_0_0_4px_rgba(30,156,150,0.28)]"
            >
              <span className="grid size-12 place-items-center rounded-[14px] bg-[#24343B] text-hielo">
                <ChartLine aria-hidden="true" className="size-6.5" />
              </span>
              <span className="font-display text-[22px] leading-tight font-bold">{t.welcome.scientificTitle}</span>
              <span className="text-[16px] leading-normal text-niebla-suave">
                {t.welcome.scientificText}
              </span>
              <span className="mt-auto inline-flex min-h-11 items-center self-start rounded-full bg-hielo px-5 font-display text-[15px] font-semibold text-hielo-tinta">
                {t.welcome.scientificButton}
              </span>
            </button>
          </div>

          <p className="flex items-start gap-2.5 text-[15px] leading-normal text-tinta-suave">
            <ArrowLeftRight aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-bosque" />
            {t.welcome.switchHint}
          </p>
        </section>

        <section aria-label={t.welcome.previewLabel} className="flex min-w-0 flex-[1.25_1_520px] flex-col gap-4">
          <div role="group" aria-label={t.variables.groupLabel} className="flex flex-wrap gap-2">
            {VARIABLE_IDS.map((id) => {
              const selected = id === variable;
              const color = variables[id].display.identityColor;
              return (
                <button
                  key={id}
                  type="button"
                  aria-pressed={selected}
                  onClick={() => {
                    setVariable(id);
                    setAuto(false);
                  }}
                  style={selected ? { backgroundColor: color, borderColor: color } : undefined}
                  className={cn(
                    "inline-flex min-h-11 items-center gap-2 rounded-full border-[1.5px] pr-4 pl-3 font-display text-[15px] font-semibold transition-colors",
                    selected ? "text-white" : "border-[#7E948E] bg-superficie text-tinta",
                  )}
                >
                  <VariableIcon variable={id} />
                  {variables[id].shortLabel}
                </button>
              );
            })}
          </div>
          <MosaicMap variable={variable} />
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-4">
            <div className="min-w-0 flex-[1_1_240px]">
              <p className="font-display text-[19px] font-bold">{v.name}</p>
              <p className="mt-1 text-[16px] leading-normal text-tinta-suave">{t.welcome.descriptions[variable]}</p>
            </div>
            <div className="min-w-[220px] flex-[0_1_300px]">
              <div className="flex gap-0.5 rounded-md border border-linea bg-superficie p-0.5">
                {v.display.ramp.map((c) => (
                  <span key={c} className="h-3.5 flex-1 rounded-[2px]" style={{ backgroundColor: c }} />
                ))}
              </div>
              <div className="mt-1.5 flex justify-between text-sm">
                <span>{v.display.words.low}</span>
                <span>{v.display.words.high}</span>
              </div>
              <p className="mt-0.5 font-display text-[13px] font-medium text-tinta-suave font-semicondensada">
                {t.welcome.unitSource(v.unitLong, v.product.shortName)}
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-between gap-3 border-t border-linea pt-3">
            <p className="flex-[1_1_280px] text-sm leading-snug text-tinta-suave">
              {t.welcome.simulatedNote}
            </p>
            <Button variant="secondary" size="sm" onClick={() => setAuto((a) => !a)}>
              {auto ? <Pause aria-hidden="true" /> : <Play aria-hidden="true" />}
              {auto ? t.welcome.pauseTour : t.welcome.resumeTour}
            </Button>
          </div>
        </section>
      </main>

      <section id="fuentes" aria-labelledby="titulo-cobertura" className="mx-auto max-w-[1320px] px-5 pb-10 sm:px-10">
        <div className="flex flex-wrap gap-x-16 gap-y-6 border-t border-linea pt-8">
          <div className="max-w-[400px] flex-[1_1_300px]">
            <h2 id="titulo-cobertura" className="text-[26px] leading-tight font-bold">
              {t.welcome.coverageTitle}
            </h2>
            <p className="mt-2.5 text-[16px] leading-relaxed text-tinta-suave">
              {t.welcome.coverageText}
            </p>
          </div>
          <div className="flex min-w-0 flex-[2_1_520px] flex-col gap-3.5">
            {VARIABLE_IDS.map((id) => {
              const item = variables[id];
              const left = position(item.availability.start, "start");
              const right = 100 - position(item.availability.end, "end");
              return (
                <div key={id} className="flex flex-wrap items-center gap-x-5 gap-y-1.5">
                  <div className="flex flex-[0_0_260px] items-center gap-3">
                    <span
                      className="grid size-9 shrink-0 place-items-center rounded-[10px] text-white"
                      style={{ backgroundColor: item.display.identityColor }}
                    >
                      <VariableIcon variable={id} />
                    </span>
                    <div>
                      <p className="font-display text-[15px] font-semibold">{item.shortLabel}</p>
                      <p className="text-[13px] text-tinta-suave">
                        {t.welcome.coverageRange(
                          item.product.shortName,
                          humanYm(item.availability.start, lang),
                          humanYm(item.availability.end, lang),
                        )}
                      </p>
                    </div>
                  </div>
                  <div
                    role="img"
                    aria-label={t.welcome.coverageAria(
                      item.name,
                      humanYm(item.availability.start, lang),
                      humanYm(item.availability.end, lang),
                    )}
                    className="relative h-3 min-w-0 flex-[1_1_240px] rounded-md bg-[#DCE5E1]"
                  >
                    <div
                      className="absolute inset-y-0 rounded-md"
                      style={{ left: `${left}%`, right: `${right}%`, backgroundColor: item.display.identityColor }}
                    />
                  </div>
                </div>
              );
            })}
            <div
              aria-hidden="true"
              className="ml-auto flex w-full max-w-[calc(100%-280px)] justify-between font-display text-[13px] text-tinta-suave font-semicondensada cifras max-sm:max-w-full"
            >
              <span>2000</span>
              <span>2005</span>
              <span>2010</span>
              <span>2015</span>
              <span>2020</span>
              <span>2025</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="mx-auto flex max-w-[1320px] flex-wrap justify-between gap-x-8 gap-y-2 px-5 pt-5 pb-10 text-sm text-tinta-suave sm:px-10">
        <p>{t.welcome.footerSources}</p>
        <p>{t.welcome.footerIllustrative}</p>
      </footer>
    </div>
  );
}
