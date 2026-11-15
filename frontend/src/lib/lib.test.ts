import { describe, expect, it } from "vitest";

import { VARIABLES } from "@/config/variables";
import { classIndex, classLabels, colorFor } from "@/lib/classify";
import { clampToRange, humanYm, inRange, stepWithin } from "@/lib/dates";
import { formatCoord, formatNumber } from "@/lib/format";

describe("fechas", () => {
  const range = { start: "2004-10", end: "2025-09" };
  it("detecta meses dentro y fuera del rango", () => {
    expect(inRange({ year: 2004, month: 9 }, range)).toBe(false);
    expect(inRange({ year: 2004, month: 10 }, range)).toBe(true);
  });
  it("ajusta al mes disponible más cercano", () => {
    expect(clampToRange({ year: 2001, month: 1 }, range)).toEqual({ year: 2004, month: 10 });
    expect(clampToRange({ year: 2025, month: 12 }, range)).toEqual({ year: 2025, month: 9 });
  });
  it("no sale del rango al avanzar", () => {
    expect(stepWithin({ year: 2025, month: 9 }, 1, range)).toBeNull();
  });
  it("escribe fechas en español", () => {
    expect(humanYm("2015-07")).toBe("julio de 2015");
  });
  it("y en inglés", () => {
    expect(humanYm("2015-07", "en")).toBe("July 2015");
    expect(formatCoord(19.43, -99.13, "en")).toBe("19.43° N, 99.13° W");
    expect(formatCoord(19.43, -99.13)).toBe("19.43° N, 99.13° O");
  });
});

describe("clases de color", () => {
  const display = VARIABLES.precipitation.display;
  it("asigna la clase según los cortes", () => {
    expect(classIndex(0, display.breaks)).toBe(0);
    expect(classIndex(5, display.breaks)).toBe(1);
    expect(classIndex(1000, display.breaks)).toBe(8);
  });
  it("sin dato no tiene color (nunca es cero)", () => {
    expect(colorFor(null, display)).toBeNull();
    expect(colorFor(0, display)).toBe(display.ramp[0]);
  });
  it("genera 9 etiquetas legibles", () => {
    const labels = classLabels(display);
    expect(labels).toHaveLength(9);
    expect(labels[0]).toBe("< 5.0");
    expect(labels[8]).toBe("≥ 250");
  });
});

describe("formato de números", () => {
  it("usa punto decimal y espacio fino en miles", () => {
    expect(formatNumber(1024.6)).toBe("1 025");
    expect(formatNumber(12.345, 2)).toBe("12.35");
    expect(formatNumber(null)).toBe("—");
  });
});
