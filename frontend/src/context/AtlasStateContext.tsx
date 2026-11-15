import { createContext, useContext, useEffect, useMemo, useReducer, type Dispatch, type ReactNode } from "react";

import { useLanguage } from "@/i18n/language";

import { atlasReducer, stateFromSearch, stateToSearch, type AtlasAction, type AtlasState } from "./atlasState";

interface AtlasContextValue {
  state: AtlasState;
  dispatch: Dispatch<AtlasAction>;
}

const AtlasContext = createContext<AtlasContextValue | null>(null);

/**
 * Proveedor del estado del Atlas. Lee el estado inicial de la URL, la
 * actualiza con cada cambio (sin crear entradas de historial nuevas) y
 * responde al botón "atrás" del navegador.
 */
export function AtlasStateProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(atlasReducer, undefined, () => stateFromSearch(window.location.search));
  const { lang } = useLanguage();

  useEffect(() => {
    const search = stateToSearch(state, lang);
    if (window.location.search !== search) {
      window.history.replaceState(window.history.state, "", `${window.location.pathname}${search}`);
    }
  }, [state, lang]);

  useEffect(() => {
    const onPop = () => dispatch({ type: "replace", state: stateFromSearch(window.location.search) });
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, []);

  const value = useMemo(() => ({ state, dispatch }), [state]);
  return <AtlasContext.Provider value={value}>{children}</AtlasContext.Provider>;
}

export function useAtlas(): AtlasContextValue {
  const context = useContext(AtlasContext);
  if (!context) throw new Error("useAtlas debe usarse dentro de <AtlasStateProvider>.");
  return context;
}
