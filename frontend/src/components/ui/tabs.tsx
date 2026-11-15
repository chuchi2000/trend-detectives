import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: string;
  content: ReactNode;
}

/**
 * Pestañas accesibles (patrón WAI-ARIA): flechas izquierda/derecha para
 * moverse, Inicio/Fin para ir a la primera o la última.
 */
export function Tabs({
  items,
  value,
  onChange,
  label,
  className,
}: {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  label: string;
  className?: string;
}) {
  const baseId = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);
  const current = Math.max(
    0,
    items.findIndex((item) => item.id === value),
  );

  const onKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    let next = current;
    if (event.key === "ArrowRight") next = (current + 1) % items.length;
    else if (event.key === "ArrowLeft") next = (current - 1 + items.length) % items.length;
    else if (event.key === "Home") next = 0;
    else if (event.key === "End") next = items.length - 1;
    else return;
    event.preventDefault();
    const item = items[next];
    if (item) {
      onChange(item.id);
      refs.current[next]?.focus();
    }
  };

  const active = items[current];
  return (
    <div className={cn("flex min-h-0 flex-col", className)}>
      <div
        role="tablist"
        aria-label={label}
        onKeyDown={onKeyDown}
        className="flex gap-1 overflow-x-auto border-b border-borde px-1"
      >
        {items.map((item, index) => {
          const selected = index === current;
          return (
            <button
              key={item.id}
              ref={(el) => {
                refs.current[index] = el;
              }}
              id={`${baseId}-tab-${item.id}`}
              role="tab"
              type="button"
              aria-selected={selected}
              aria-controls={`${baseId}-panel-${item.id}`}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(item.id)}
              className={cn(
                "-mb-px min-h-11 shrink-0 border-b-[3px] px-3 font-display text-sm font-semibold transition-colors",
                selected ? "border-acento text-texto" : "border-transparent text-texto-suave hover:text-texto",
              )}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {active && (
        <div
          role="tabpanel"
          id={`${baseId}-panel-${active.id}`}
          aria-labelledby={`${baseId}-tab-${active.id}`}
          className="min-h-0 flex-1 overflow-y-auto"
        >
          {active.content}
        </div>
      )}
    </div>
  );
}
