import { describe, expect, it } from "vitest";

import { DEFAULT_STATE, atlasReducer, regionParam, stateFromSearch, stateToSearch } from "./atlasState";

describe("estado compartido del Atlas", () => {
  it("cambiar de modo conserva variable, fecha, región y punto", () => {
    const start = {
      ...DEFAULT_STATE,
      variable: "temperature" as const,
      date: { year: 2012, month: 4 },
      region: { level: "state" as const, code: "24", name: "San Luis Potosí" },
      point: { lat: 22.15, lon: -100.98 },
    };
    const next = atlasReducer(start, { type: "setMode", mode: "cientifico" });
    expect(next.mode).toBe("cientifico");
    expect(next.variable).toBe("temperature");
    expect(next.date).toEqual({ year: 2012, month: 4 });
    expect(next.region).toEqual(start.region);
    expect(next.point).toEqual(start.point);
  });

  it("al elegir NO₂ con una fecha anterior a octubre de 2004 la ajusta y avisa", () => {
    const start = { ...DEFAULT_STATE, date: { year: 2002, month: 6 } };
    const next = atlasReducer(start, { type: "setVariable", variable: "no2" });
    expect(next.date).toEqual({ year: 2004, month: 10 });
    expect(next.notice).toContain("octubre de 2004");
  });

  it("no avanza más allá del último mes disponible", () => {
    const start = { ...DEFAULT_STATE, variable: "precipitation" as const, date: { year: 2025, month: 9 } };
    const next = atlasReducer(start, { type: "stepMonth", step: 1 });
    expect(next.date).toEqual({ year: 2025, month: 9 });
    expect(next.notice).toBeTruthy();
  });

  it("avanza y retrocede de mes cruzando años", () => {
    const start = { ...DEFAULT_STATE, date: { year: 2010, month: 12 } };
    expect(atlasReducer(start, { type: "stepMonth", step: 1 }).date).toEqual({ year: 2011, month: 1 });
    expect(atlasReducer(start, { type: "stepMonth", step: -12 }).date).toEqual({ year: 2009, month: 12 });
  });

  it("el estado viaja por la URL y vuelve igual", () => {
    const state = {
      ...DEFAULT_STATE,
      mode: "cientifico" as const,
      variable: "evapotranspiration" as const,
      date: { year: 2018, month: 8 },
      compare: { enabled: true, date: { year: 2008, month: 8 } },
      region: { level: "municipality" as const, code: "24028", name: "San Luis Potosí" },
      point: { lat: 22.1565, lon: -100.9855 },
      layers: { data: true, states: false, municipalities: true },
    };
    const restored = stateFromSearch(stateToSearch(state));
    expect(restored).toEqual({ ...state, notice: null });
  });

  it("ignora parámetros inválidos de la URL", () => {
    const restored = stateFromSearch("?modo=otro&variable=lluvia&fecha=2015-13&punto=abc");
    expect(restored.mode).toBe(DEFAULT_STATE.mode);
    expect(restored.variable).toBe(DEFAULT_STATE.variable);
    expect(restored.date).toEqual(DEFAULT_STATE.date);
    expect(restored.point).toBeNull();
  });

  it("traduce la región al formato de la API", () => {
    expect(regionParam(null)).toBe("nacional");
    expect(regionParam({ level: "state", code: "24", name: "SLP" })).toBe("estado:24");
    expect(regionParam({ level: "municipality", code: "24028", name: "SLP" })).toBe("municipio:24028");
  });
});
