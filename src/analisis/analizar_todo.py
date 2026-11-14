"""Corre el análisis de tendencia para todas las series limpias. (Persona 2)

Uso (después de limpiar los datos):
    python src/analisis/analizar_todo.py

Lee data/processed/<variable>/<region>.csv y escribe:
  - data/processed/<variable>/tendencias.json        → lo que pinta el mapa
  - data/processed/<variable>/series/<region>.json   → la gráfica al dar clic
  - data/processed/resumen_tendencias.csv            → tabla para revisar a ojo
"""

import json
from pathlib import Path

import pandas as pd

from tendencias import analizar_tendencia, quitar_estacionalidad

RAIZ = Path(__file__).resolve().parents[2]
DATOS = RAIZ / "data" / "processed"


def leer_serie(ruta: Path) -> pd.Series:
    tabla = pd.read_csv(ruta)
    return pd.Series(tabla["valor"].values, index=pd.to_datetime(tabla["fecha"]))


def main():
    catalogo = json.loads((DATOS / "catalogo.json").read_text(encoding="utf-8"))
    filas = []

    for variable, info_var in catalogo["variables"].items():
        zonas = []
        for ruta in sorted((DATOS / variable).glob("*.csv")):
            region = ruta.stem
            info_reg = catalogo["regiones"][region]
            serie = leer_serie(ruta)
            r = analizar_tendencia(serie)

            zonas.append({"id": region, "nombre": info_reg["nombre"],
                          "lat": info_reg["lat"], "lon": info_reg["lon"], **r})

            anom = quitar_estacionalidad(serie.dropna()).reindex(serie.index)
            destino = DATOS / variable / "series" / f"{region}.json"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(json.dumps({
                "id": region,
                "fechas": [f"{f:%Y-%m}" for f in serie.index],
                "valores": [None if pd.isna(v) else round(float(v), 4) for v in serie.values],
                "anomalias": [None if pd.isna(v) else round(float(v), 4) for v in anom.values],
            }, ensure_ascii=False), encoding="utf-8")

            filas.append({"variable": variable, "region": info_reg["nombre"],
                          "unidades": info_var["unidades"], **{k: v for k, v in r.items() if k != "ic95"},
                          "ic95_bajo": r["ic95"][0], "ic95_alto": r["ic95"][1]})

        periodo = {"inicio": min(z["inicio"] for z in zonas), "fin": max(z["fin"] for z in zonas)}
        (DATOS / variable / "tendencias.json").write_text(json.dumps({
            "variable": variable, **info_var, "periodo": periodo, "zonas": zonas,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    resumen = pd.DataFrame(filas)
    resumen.to_csv(DATOS / "resumen_tendencias.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print(resumen[["variable", "region", "pendiente_por_decada", "unidades",
                       "cambio_pct_por_decada", "p_valor", "significativa"]].to_string(index=False))


if __name__ == "__main__":
    main()
