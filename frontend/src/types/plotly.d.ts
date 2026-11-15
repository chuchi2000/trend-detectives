/**
 * Tipos mínimos de plotly.js-dist-min: solo lo que usa el Atlas.
 * Así no dependemos de un paquete de tipos externo que puede quedar desfasado.
 */
declare module "plotly.js-dist-min" {
  export interface PlotData {
    type?: "scatter" | "bar";
    mode?: string;
    name?: string;
    x: Array<string | number>;
    y: Array<number | null>;
    yaxis?: string;
    line?: { color?: string; width?: number; dash?: string };
    marker?: { color?: string | string[]; size?: number };
    connectgaps?: boolean;
    hovertemplate?: string;
  }
  export type Layout = Record<string, unknown>;
  export type Config = Record<string, unknown>;
  export function react(root: HTMLElement, data: PlotData[], layout?: Layout, config?: Config): Promise<unknown>;
  export function purge(root: HTMLElement): void;
  export const Plots: { resize(root: HTMLElement): void };
  const Plotly: {
    react: typeof react;
    purge: typeof purge;
    Plots: typeof Plots;
  };
  export default Plotly;
}
