/**
 * Idioma activo de la interfaz (español por defecto).
 *
 * Fuera de <LanguageProvider> (por ejemplo, en pruebas de un componente suelto)
 * el contexto vale español, así que los componentes funcionan sin proveedor.
 */
import { createContext, useContext } from "react";

import { VARIABLES_BY_LANG, type VariableConfig, type VariableId } from "@/config/variables";
import { MESSAGES, type Messages } from "@/i18n/messages";
import type { Lang } from "@/lib/dates";

export type { Lang };

export const LANG_STORAGE_KEY = "atlas-idioma";

export interface LanguageValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: Messages;
}

export const LanguageContext = createContext<LanguageValue>({
  lang: "es",
  setLang: () => undefined,
  t: MESSAGES.es,
});

export function useLanguage(): LanguageValue {
  return useContext(LanguageContext);
}

/** Variables (nombres, unidades, advertencias) en el idioma activo. */
export function useVariables(): Record<VariableId, VariableConfig> {
  return VARIABLES_BY_LANG[useLanguage().lang];
}

export function isLang(value: string | null | undefined): value is Lang {
  return value === "es" || value === "en";
}

/** Idioma inicial: ?lang= de la URL (enlace compartido) y, si no, la última elección guardada. */
export function readInitialLang(): Lang {
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  if (isLang(fromUrl)) return fromUrl;
  try {
    const saved = window.localStorage.getItem(LANG_STORAGE_KEY);
    if (isLang(saved)) return saved;
  } catch {
    // Sin almacenamiento local (modo privado): se usa español.
  }
  return "es";
}
