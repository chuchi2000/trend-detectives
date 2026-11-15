import { BookOpen, Database, Home, Menu, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useLanguage } from "@/i18n/language";

export interface MenuAction {
  id: string;
  label: string;
  description: string;
  icon: "inicio" | "glosario" | "fuentes";
  onSelect: () => void;
}

const ICONS = { inicio: Home, glosario: BookOpen, fuentes: Database };

/**
 * Menú principal desplegable. Se cierra con Escape, al hacer clic fuera o al
 * elegir una opción; el foco vuelve al botón que lo abrió.
 */
export function MainMenu({ actions }: { actions: MenuAction[] }) {
  const [open, setOpen] = useState(false);
  const { t } = useLanguage();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
        buttonRef.current?.focus();
      }
    };
    const onClick = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!menuRef.current?.contains(target) && !buttonRef.current?.contains(target)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    menuRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  return (
    <div className="relative">
      <Button
        ref={buttonRef}
        variant="ghost"
        size="icon"
        aria-label={open ? t.header.closeMenu : t.header.openMenu}
        aria-expanded={open}
        aria-haspopup="true"
        onClick={() => setOpen((o) => !o)}
      >
        {open ? <X aria-hidden="true" /> : <Menu aria-hidden="true" />}
      </Button>
      {open && (
        <div
          ref={menuRef}
          className="absolute top-full right-0 z-50 mt-2 w-72 rounded-2xl border border-borde bg-panel p-2 shadow-[0_12px_32px_rgba(16,48,42,0.18)]"
        >
          {actions.map((action) => {
            const Icon = ICONS[action.icon];
            return (
              <button
                key={action.id}
                type="button"
                onClick={() => {
                  setOpen(false);
                  action.onSelect();
                }}
                className="flex w-full items-start gap-3 rounded-xl p-3 text-left hover:bg-panel-2"
              >
                <Icon aria-hidden="true" className="mt-0.5 size-5 text-acento" />
                <span className="flex flex-col">
                  <span className="font-display font-semibold text-texto">{action.label}</span>
                  <span className="text-sm text-texto-suave">{action.description}</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
