import { useEffect, useMemo, useState, type ReactNode } from "react";

import { LANG_STORAGE_KEY, LanguageContext, readInitialLang, type Lang } from "@/i18n/language";
import { MESSAGES } from "@/i18n/messages";
import { setApiLanguage } from "@/services/api";

/**
 * Proveedor del idioma. Guarda la elección en el navegador, la refleja en la URL
 * (?lang=en, para compartir enlaces), actualiza <html lang> y hace que la API
 * responda en el mismo idioma (mensajes, frases de tendencia, metadatos).
 */
export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(readInitialLang);

  // Antes de que los hijos consulten la API: los efectos de los hijos corren
  // antes que los del padre, así que esto no puede esperar a un useEffect.
  setApiLanguage(lang);

  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      window.localStorage.setItem(LANG_STORAGE_KEY, lang);
    } catch {
      // Sin almacenamiento local: la elección dura lo que dure la pestaña.
    }
    const url = new URL(window.location.href);
    if (lang === "en") url.searchParams.set("lang", "en");
    else url.searchParams.delete("lang");
    if (url.href !== window.location.href) window.history.replaceState(window.history.state, "", url);
  }, [lang]);

  const value = useMemo(() => ({ lang, setLang, t: MESSAGES[lang] }), [lang]);
  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}
