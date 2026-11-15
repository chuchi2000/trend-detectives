import { AlertTriangle, Info, Loader2 } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/** Mensajes de estado: cargando, sin datos, error o aviso. */
export function StatusMessage({
  kind,
  title,
  children,
  className,
}: {
  kind: "loading" | "empty" | "error" | "info";
  title?: string;
  children?: ReactNode;
  className?: string;
}) {
  const Icon = kind === "loading" ? Loader2 : kind === "error" ? AlertTriangle : Info;
  return (
    <div
      role={kind === "error" ? "alert" : "status"}
      className={cn(
        "flex gap-3 rounded-2xl border p-4 text-sm",
        kind === "error" ? "border-[#c24535]/50 bg-[#c24535]/8" : "border-borde bg-panel",
        className,
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn("mt-0.5 size-5 shrink-0", kind === "loading" && "animate-spin", kind === "error" ? "text-[#c24535]" : "text-enlace")}
      />
      <div className="flex flex-col gap-1">
        {title && <p className="font-display font-semibold text-texto">{title}</p>}
        {children && <div className="leading-relaxed text-texto-suave">{children}</div>}
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn("animate-pulse rounded-lg bg-panel-2", className)} />;
}
