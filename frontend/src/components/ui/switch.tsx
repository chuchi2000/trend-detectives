import { useId } from "react";

import { cn } from "@/lib/utils";

/** Interruptor accesible (role="switch") para activar o desactivar capas. */
export function Switch({
  checked,
  onChange,
  label,
  description,
}: {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: string;
  description?: string;
}) {
  const id = useId();
  return (
    <div className="flex min-h-11 items-center justify-between gap-3">
      <label htmlFor={id} className="flex flex-col">
        <span className="text-[15px] text-texto">{label}</span>
        {description && <span className="text-xs text-texto-suave">{description}</span>}
      </label>
      <button
        id={id}
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cn(
          "relative h-7 w-12 shrink-0 rounded-full border-[1.5px] transition-colors",
          checked ? "border-acento bg-acento" : "border-borde-fuerte bg-panel-2",
        )}
      >
        <span
          className={cn(
            "absolute top-1/2 size-5 -translate-y-1/2 rounded-full transition-all",
            checked ? "left-[22px] bg-acento-texto" : "left-0.5 bg-borde-fuerte",
          )}
        />
      </button>
    </div>
  );
}
