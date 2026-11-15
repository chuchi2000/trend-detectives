import type { VariableDisplay } from "@/config/variables";
import { classIndex, hexToRgb } from "@/lib/classify";
import type { GridPayload } from "@/services/types";

/**
 * Convierte la malla de valores (modo DEMO o malla comparativa) en una imagen
 * PNG donde cada celda es un píxel con el color de su clase. MapLibre la
 * coloca sobre el mapa con remuestreo "nearest" para conservar los píxeles.
 */
export function gridToImage(grid: GridPayload, display: VariableDisplay): string {
  const canvas = document.createElement("canvas");
  canvas.width = grid.nx;
  canvas.height = grid.ny;
  const ctx = canvas.getContext("2d");
  if (!ctx) return "";
  const image = ctx.createImageData(grid.nx, grid.ny);
  const colors = display.ramp.map(hexToRgb);
  grid.values.forEach((value, i) => {
    if (value === null || !Number.isFinite(value)) return;
    const [r, g, b] = colors[classIndex(value, display.breaks)] ?? [0, 0, 0];
    image.data[i * 4] = r;
    image.data[i * 4 + 1] = g;
    image.data[i * 4 + 2] = b;
    image.data[i * 4 + 3] = 235;
  });
  ctx.putImageData(image, 0, 0);
  return canvas.toDataURL("image/png");
}

/** Esquinas de la imagen en el orden que pide MapLibre: NO, NE, SE, SO. */
export function gridCorners(grid: GridPayload): [[number, number], [number, number], [number, number], [number, number]] {
  return [
    [grid.west, grid.north],
    [grid.east, grid.north],
    [grid.east, grid.south],
    [grid.west, grid.south],
  ];
}
