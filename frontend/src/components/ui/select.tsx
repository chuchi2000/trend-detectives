import { ChevronDown } from "lucide-react";
import { useId, type SelectHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

/**
 * Selector desplegable basado en <select> nativo: funciona con teclado,
 * lectores de pantalla y el selector propio de cada teléfono.
 */
export function Select({
  label,
  hideLabel = false,
  options,
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; hideLabel?: boolean; options: SelectOption[] }) {
  const id = useId();
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <label htmlFor={id} className={cn("text-xs font-semibold text-texto-suave", hideLabel && "sr-only")}>
        {label}
      </label>
      <div className="relative">
        <select
          id={id}
          className="min-h-11 w-full appearance-none rounded-xl border-[1.5px] border-borde-fuerte bg-panel py-2 pr-9 pl-3 font-display text-[15px] font-semibold text-texto"
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value} disabled={option.disabled}>
              {option.label}
            </option>
          ))}
        </select>
        <ChevronDown
          aria-hidden="true"
          className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-texto-suave"
        />
      </div>
    </div>
  );
}
