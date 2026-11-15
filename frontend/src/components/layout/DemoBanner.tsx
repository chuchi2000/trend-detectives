import { FlaskConical } from "lucide-react";

import { useLanguage } from "@/i18n/language";
import type { DataMode } from "@/services/types";

/**
 * Aviso permanente de modo DEMO. Separa con claridad los datos simulados de
 * los datos reales: mientras el backend responda "mode": "demo", este aviso
 * no se puede ocultar.
 */
export function DemoBanner({ mode }: { mode: DataMode | null }) {
  const { t } = useLanguage();
  if (mode !== "demo") return null;
  return (
    <div role="note" className="flex items-center justify-center gap-2 bg-sol px-4 py-1.5 text-center text-sm text-tinta">
      <FlaskConical aria-hidden="true" className="size-4 shrink-0" />
      <span>
        <strong className="font-display">{t.demoBanner.title}</strong> {t.demoBanner.text}
      </span>
    </div>
  );
}
