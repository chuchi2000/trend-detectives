import { FlaskConical } from "lucide-react";

import type { DataMode } from "@/services/types";

/**
 * Aviso permanente de modo DEMO. Separa con claridad los datos simulados de
 * los datos reales: mientras el backend responda "mode": "demo", este aviso
 * no se puede ocultar.
 */
export function DemoBanner({ mode }: { mode: DataMode | null }) {
  if (mode !== "demo") return null;
  return (
    <div role="note" className="flex items-center justify-center gap-2 bg-sol px-4 py-1.5 text-center text-sm text-tinta">
      <FlaskConical aria-hidden="true" className="size-4 shrink-0" />
      <span>
        <strong className="font-display">Modo DEMOSTRACIÓN:</strong> los valores son simulados para probar la
        interfaz. No son mediciones de NASA.
      </span>
    </div>
  );
}
