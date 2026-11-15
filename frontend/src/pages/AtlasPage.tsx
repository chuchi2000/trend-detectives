import { PanelRightClose, PanelRightOpen, Sun, MoonStar, X } from "lucide-react";
import { useEffect, useState } from "react";

import { LogoLockup } from "@/components/brand/Logo";
import { ExplorerPanel } from "@/components/educational/ExplorerPanel";
import { DemoBanner } from "@/components/layout/DemoBanner";
import { AtlasMap } from "@/components/maps/AtlasMap";
import { MapLegend } from "@/components/maps/MapLegend";
import { MainMenu } from "@/components/navigation/MainMenu";
import { ModeSwitch } from "@/components/navigation/ModeSwitch";
import { VariableSelector } from "@/components/navigation/VariableSelector";
import { ScientificPanel } from "@/components/scientific/ScientificPanel";
import { TimeControls } from "@/components/temporal/TimeControls";
import { Timeline } from "@/components/temporal/Timeline";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusMessage } from "@/components/ui/status";
import { useAtlas } from "@/context/AtlasStateContext";
import { VARIABLES } from "@/config/variables";
import { useApi } from "@/hooks/useApi";
import { capitalize, humanYm } from "@/lib/dates";
import { cn } from "@/lib/utils";
import { api } from "@/services/api";

const THEME_KEY = "atlas-tema-cientifico";

function readScientificTheme(): "claro" | "oscuro" {
  try {
    return window.localStorage.getItem(THEME_KEY) === "claro" ? "claro" : "oscuro";
  } catch {
    return "oscuro";
  }
}

/**
 * Área de exploración: encabezado con selector de modo, selección de variable
 * y fecha, mapa interactivo y panel lateral del modo activo.
 * El mapa y el estado son los mismos en los dos modos.
 */
export function AtlasPage({ onHome }: { onHome: () => void }) {
  const { state, dispatch } = useAtlas();
  const [panelOpen, setPanelOpen] = useState(true);
  const [explorerTab, setExplorerTab] = useState<string | null>(null);
  const [scientificTheme, setScientificTheme] = useState(readScientificTheme);
  const theme = state.mode === "explorador" ? "claro" : scientificTheme;

  useEffect(() => {
    try {
      window.localStorage.setItem(THEME_KEY, scientificTheme);
    } catch {
      // El almacenamiento local puede no estar disponible (modo privado); no es grave.
    }
  }, [scientificTheme]);

  useEffect(() => {
    document.documentElement.dataset.tema = theme;
    return () => {
      delete document.documentElement.dataset.tema;
    };
  }, [theme]);

  const health = useApi((signal) => api.health(signal), []);
  const layer = useApi(
    (signal) => api.layer(state.variable, state.date.year, state.date.month, signal),
    [state.variable, state.date.year, state.date.month],
  );
  const mode = health.data?.mode ?? layer.data?.mode ?? null;
  const v = VARIABLES[state.variable];

  return (
    <div data-tema={theme} className="flex min-h-dvh flex-col bg-fondo text-texto lg:h-dvh">
      <DemoBanner mode={mode} />
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-borde px-4 py-2.5 sm:px-6">
        <button type="button" onClick={onHome} className="rounded-lg text-texto" aria-label="Ir a la pantalla de bienvenida">
          <LogoLockup theme={theme} />
        </button>
        <div className="flex items-center gap-2">
          <ModeSwitch mode={state.mode} onChange={(m) => dispatch({ type: "setMode", mode: m })} />
          {state.mode === "cientifico" && (
            <Button
              size="icon"
              variant="ghost"
              aria-label={scientificTheme === "oscuro" ? "Usar tema claro" : "Usar tema oscuro"}
              onClick={() => setScientificTheme((t) => (t === "oscuro" ? "claro" : "oscuro"))}
            >
              {scientificTheme === "oscuro" ? <Sun aria-hidden="true" /> : <MoonStar aria-hidden="true" />}
            </Button>
          )}
          <MainMenu
            actions={[
              { id: "inicio", label: "Inicio", description: "Volver a la pantalla de bienvenida", icon: "inicio", onSelect: onHome },
              {
                id: "glosario",
                label: "Glosario ambiental",
                description: "Definiciones sencillas de los términos",
                icon: "glosario",
                onSelect: () => {
                  dispatch({ type: "setMode", mode: "explorador" });
                  setExplorerTab("glosario");
                  setPanelOpen(true);
                },
              },
              {
                id: "fuentes",
                label: "Fuentes y metadatos",
                description: "Productos NASA, versiones y calidad",
                icon: "fuentes",
                onSelect: () => {
                  dispatch({ type: "setMode", mode: "cientifico" });
                  setPanelOpen(true);
                },
              },
            ]}
          />
        </div>
      </header>

      <div className="flex flex-col gap-3 border-b border-borde px-4 py-3 sm:px-6 xl:flex-row xl:items-center xl:justify-between">
        <VariableSelector value={state.variable} onChange={(id) => dispatch({ type: "setVariable", variable: id })} />
        <TimeControls />
      </div>

      {state.notice && (
        <div role="status" className="flex items-start justify-between gap-3 bg-sol-claro px-4 py-2 text-sm text-tinta sm:px-6">
          <span>{state.notice}</span>
          <button type="button" aria-label="Cerrar aviso" onClick={() => dispatch({ type: "dismissNotice" })}>
            <X aria-hidden="true" className="size-4" />
          </button>
        </div>
      )}

      <main className="flex min-h-0 flex-1 flex-col gap-3 p-3 sm:p-4 lg:flex-row">
        <section aria-label="Mapa" className="flex min-h-[62vh] min-w-0 flex-1 flex-col gap-2 lg:min-h-0">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 className="text-xl font-bold">
                {v.name} · {capitalize(humanYm(state.date))}
              </h1>
              {layer.data && (
                <span className="font-display text-xs text-texto-suave font-semicondensada">
                  {layer.data.source} · {layer.data.resolution}
                </span>
              )}
              {mode === "demo" && <Badge tone="demo">Simulado</Badge>}
              {layer.data?.quality.flags.includes("deriva_orbital_terra") && (
                <Badge tone="warning">Deriva orbital de Terra</Badge>
              )}
            </div>
            <Button
              size="sm"
              variant="ghost"
              className="hidden lg:inline-flex"
              aria-expanded={panelOpen}
              onClick={() => setPanelOpen((o) => !o)}
            >
              {panelOpen ? <PanelRightClose aria-hidden="true" /> : <PanelRightOpen aria-hidden="true" />}
              {panelOpen ? "Ocultar panel" : "Mostrar panel"}
            </Button>
          </div>
          <div className="relative flex min-h-0 flex-1 flex-col">
            <AtlasMap layer={layer.data} theme={theme} />
            {layer.status === "loading" && (
              <p className="absolute top-3 left-3 rounded-full bg-panel/95 px-3 py-1 text-xs text-texto-suave">Cargando capa…</p>
            )}
            {layer.status === "error" && (
              <div className="absolute inset-x-3 top-3 max-w-md">
                <StatusMessage kind={layer.error.code === "sin_conexion" ? "error" : "empty"} title="Sin capa para esta fecha">
                  {layer.error.message}
                </StatusMessage>
              </div>
            )}
          </div>
          {!panelOpen && (
            <div className="rounded-2xl border border-borde bg-panel p-3">
              <MapLegend variable={state.variable} mode={state.mode} />
            </div>
          )}
          <Timeline />
        </section>

        {panelOpen && (
          <aside
            aria-label={state.mode === "explorador" ? "Panel del modo Explorador" : "Panel del modo Científico"}
            className={cn(
              "flex min-h-[480px] flex-col overflow-hidden rounded-[20px] border border-borde bg-panel-2/40 lg:min-h-0 lg:w-[420px] xl:w-[460px]",
            )}
          >
            {state.mode === "explorador" ? (
              <ExplorerPanel key={explorerTab ?? "observar"} initialTab={explorerTab ?? "observar"} />
            ) : (
              <ScientificPanel layer={layer.data} theme={theme} mode={mode} />
            )}
          </aside>
        )}
      </main>
    </div>
  );
}
