import type { HTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const tones = {
  neutral: "bg-panel-2 text-texto-suave",
  accent: "bg-acento-suave text-acento",
  warning: "bg-sol-claro text-tinta",
  demo: "bg-sol text-tinta",
} as const;

export function Badge({
  tone = "neutral",
  className,
  ...props
}: HTMLAttributes<HTMLSpanElement> & { tone?: keyof typeof tones }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 font-display text-xs font-semibold",
        tones[tone],
        className,
      )}
      {...props}
    />
  );
}
