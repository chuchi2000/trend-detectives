"""Limpia CSV descargados de Giovanni (Time Series, Area-Averaged). (Persona 1)

Uso:
    python src/datos/limpiar_giovanni.py data/giovanni

Para cada archivo:
  - Detecta la variable (por el nombre de la columna) y la región (por el
    "User Bounding Box" del encabezado).
  - Quita los valores de relleno (fill values) y convierte las unidades.
  - Si los datos son diarios (NO2), los pasa a promedios mensuales.
  - Guarda data/processed/<variable>/<region>.csv con columnas fecha,valor
    y actualiza data/processed/catalogo.json.
"""

import csv
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / "data" / "processed"

# Regiones de la demo: (oeste, sur, este, norte) y un punto central para el mapa
REGIONES = {
    "puebla":     {"nombre": "Puebla",           "bbox": (-98.95, 18.30, -97.45, 19.80), "lat": 19.04, "lon": -98.20},
    "cdmx":       {"nombre": "Ciudad de México", "bbox": (-99.90, 18.70, -98.40, 20.20), "lat": 19.43, "lon": -99.13},
    "monterrey":  {"nombre": "Monterrey",        "bbox": (-101.05, 24.90, -99.55, 26.40), "lat": 25.67, "lon": -100.31},
    "merida":     {"nombre": "Mérida",           "bbox": (-90.40, 19.90, -88.90, 21.30), "lat": 20.97, "lon": -89.62},
    "hermosillo": {"nombre": "Hermosillo",       "bbox": (-111.70, 28.30, -110.20, 29.80), "lat": 29.07, "lon": -110.96},
}


def _k_a_c(serie):
    return serie - 273.15


def _mmhr_a_mmmes(serie):
    # IMERG mensual viene como tasa promedio en mm/hr: se multiplica por las horas del mes
    return serie * 24 * serie.index.days_in_month


def _no2_escala(serie):
    return serie / 1e15


VARIABLES = {
    "M2TMNXSLV_5_12_4_T2M": {
        "variable": "temperatura", "nombre": "Temperatura del aire a 2 m",
        "fuente": "MERRA-2 (M2TMNXSLV v5.12.4)", "unidades": "°C",
        "convertir": _k_a_c, "diario": False,
    },
    "GPM_3IMERGM_07_precipitation": {
        "variable": "lluvia", "nombre": "Lluvia",
        "fuente": "GPM IMERG Final (GPM_3IMERGM v07)", "unidades": "mm/mes",
        "convertir": _mmhr_a_mmmes, "diario": False,
    },
    "OMNO2d_004_ColumnAmountNO2TropCloudScreened": {
        "variable": "no2", "nombre": "NO₂ troposférico (contaminación)",
        "fuente": "OMI (OMNO2d v004)", "unidades": "10¹⁵ moléculas/cm²",
        "convertir": _no2_escala, "diario": True,
    },
}

DIAS_MINIMOS_POR_MES = 5  # para datos diarios: si un mes tiene menos días válidos, queda vacío


def leer_giovanni(ruta: Path):
    """Separa el encabezado de Giovanni de la tabla de datos."""
    meta, filas, en_datos, columna = {}, [], False, None
    with open(ruta, encoding="utf-8") as f:
        for fila in csv.reader(f):
            if not fila:
                continue
            if not en_datos:
                if fila[0].strip() == "time":
                    en_datos, columna = True, fila[1].strip()
                else:
                    meta[fila[0].strip().rstrip(":")] = fila[1].strip() if len(fila) > 1 else ""
            else:
                filas.append((fila[0].strip(), fila[1].strip()))
    serie = pd.Series(
        pd.to_numeric([v for _, v in filas], errors="coerce"),
        index=pd.to_datetime([t for t, _ in filas]),
    )
    return meta, columna, serie


def identificar_region(bbox_texto: str):
    bbox = tuple(float(x) for x in bbox_texto.split(","))
    for clave, reg in REGIONES.items():
        if np.allclose(bbox, reg["bbox"], atol=0.01):
            return clave
    return None


def limpiar(ruta: Path):
    meta, columna, serie = leer_giovanni(ruta)
    clave_var = columna.removeprefix("mean_")
    if clave_var not in VARIABLES:
        print(f"  ⚠ Variable desconocida ({clave_var}), se omite: {ruta.name}")
        return None
    var = VARIABLES[clave_var]

    region = identificar_region(meta.get("User Bounding Box", ""))
    if region is None:
        print(f"  ⚠ Región no reconocida ({meta.get('User Bounding Box')}), se omite: {ruta.name}")
        return None

    # Quitar valores de relleno (fill values)
    relleno = float([v for k, v in meta.items() if k.startswith("Fill Value")][0])
    serie = serie.where(~np.isclose(serie, relleno, rtol=1e-6) & (serie.abs() < 1e20))

    # Diario -> mensual
    n_dias = None
    if var["diario"]:
        n_dias = serie.resample("MS").count()
        serie = serie.resample("MS").mean().where(n_dias >= DIAS_MINIMOS_POR_MES)

    serie = var["convertir"](serie)

    destino = SALIDA / var["variable"] / f"{region}.csv"
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabla = pd.DataFrame({"fecha": serie.index.strftime("%Y-%m"), "valor": serie.round(4).values})
    if n_dias is not None:
        tabla["dias_validos"] = n_dias.values
    tabla.to_csv(destino, index=False)

    validos = serie.dropna()
    print(f"  ✓ {var['variable']:<11} {region:<11} {validos.index.min():%Y-%m} a {validos.index.max():%Y-%m} "
          f"({len(validos)} meses) → {destino.relative_to(RAIZ)}")
    return var["variable"], region, clave_var


def main(rutas):
    catalogo = {"variables": {}, "regiones": {}}
    ruta_catalogo = SALIDA / "catalogo.json"
    if ruta_catalogo.exists():
        catalogo = json.loads(ruta_catalogo.read_text(encoding="utf-8"))

    for ruta in rutas:
        resultado = limpiar(Path(ruta))
        if resultado is None:
            continue
        variable, region, clave_var = resultado
        v = VARIABLES[clave_var]
        catalogo["variables"][variable] = {k: v[k] for k in ("nombre", "fuente", "unidades")}
        catalogo["regiones"][region] = {k: REGIONES[region][k] for k in ("nombre", "lat", "lon")} | {
            "bbox": list(REGIONES[region]["bbox"])}

    ruta_catalogo.parent.mkdir(parents=True, exist_ok=True)
    ruta_catalogo.write_text(json.dumps(catalogo, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catálogo actualizado: {ruta_catalogo.relative_to(RAIZ)}")


def expandir(argumentos):
    """Acepta archivos, carpetas o patrones (*.csv); en Windows la terminal no los expande sola."""
    rutas = []
    for arg in argumentos:
        p = Path(arg)
        if p.is_dir():
            rutas += sorted(p.glob("*.csv"))
        elif any(c in arg for c in "*?["):
            rutas += sorted(Path().glob(arg))
        else:
            rutas.append(p)
    return rutas


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python src/datos/limpiar_giovanni.py data/giovanni")
    main(expandir(sys.argv[1:]))
