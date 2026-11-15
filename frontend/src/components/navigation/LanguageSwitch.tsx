import { Languages } from "lucide-react";

import { useLanguage, type Lang } from "@/i18n/language";
import { cn } from "@/lib/utils";

/** Selector de idioma ES / EN (encabezado de la bienvenida y del Atlas). */
export function LanguageSwitch({ className }: { className?: string }) {
  const { lang, setLang, t } = useLanguage();
  const options: Array<{ id: Lang; short: string; label: string }> = [
    { id: "es", short: "ES", label: t.language.es },
    { id: "en", short: "EN", label: t.language.en },
  ];
  return (
    <div
      role="group"
      aria-label={t.language.label}
      className={cn("inline-flex items-center gap-1 rounded-full bg-panel-2 p-1", className)}
    >
      <Languages aria-hidden="true" className="mx-1 size-4 text-texto-suave" />
      {options.map((option) => {
        const active = lang === option.id;
        return (
          <button
            key={option.id}
            type="button"
            lang={option.id}
            aria-pressed={active}
            aria-label={option.label}
            title={option.label}
            onClick={() => setLang(option.id)}
            className={cn(
              "inline-flex min-h-9 min-w-10 items-center justify-center rounded-full px-2.5 font-display text-sm transition-colors",
              active
                ? "border border-borde-fuerte bg-panel font-bold text-texto"
                : "border border-transparent font-semibold text-texto-suave hover:text-texto",
            )}
          >
            {option.short}
          </button>
        );
      })}
    </div>
  );
}
