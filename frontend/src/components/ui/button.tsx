import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "@/lib/utils";

/**
 * Botón base (patrón de shadcn/ui con class-variance-authority).
 * Variantes: primary (acento del modo), secondary (contorno), ghost (sin fondo).
 * Todas miden al menos 44 px de alto para tocarse con facilidad en pantallas táctiles.
 */
export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 rounded-full font-display font-semibold whitespace-nowrap transition-colors disabled:pointer-events-none disabled:opacity-45 [&_svg]:size-4.5 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        primary: "bg-acento text-acento-texto hover:brightness-110",
        secondary: "border-[1.5px] border-borde-fuerte bg-transparent text-texto hover:bg-panel-2",
        ghost: "bg-transparent text-texto hover:bg-panel-2",
      },
      size: {
        md: "min-h-11 px-5 text-[15px]",
        sm: "min-h-9 px-3.5 text-sm",
        icon: "size-11 p-0",
      },
    },
    defaultVariants: { variant: "secondary", size: "md" },
  },
);

export type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants>;

export function Button({ className, variant, size, type = "button", ...props }: ButtonProps) {
  return <button type={type} className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
