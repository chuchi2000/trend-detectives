"""Análisis de tendencias para una serie de tiempo mensual.

Uso básico:
    from tendencias import analizar_tendencia
    resultado = analizar_tendencia(serie)   # serie: pd.Series con índice de fechas mensuales
"""

import numpy as np
import pandas as pd
import pymannkendall as mk
from scipy import stats


def quitar_estacionalidad(serie: pd.Series) -> pd.Series:
    """Resta a cada mes su promedio histórico (todos los eneros, todos los febreros...).

    Lo que queda son las anomalías: si un mes fue más alto o más bajo de lo normal.
    Sin este paso, el ciclo de las estaciones tapa la tendencia.
    """
    climatologia = serie.groupby(serie.index.month).transform("mean")
    return serie - climatologia


def analizar_tendencia(serie: pd.Series, alfa: float = 0.05) -> dict:
    """Calcula la pendiente, su intervalo de confianza y la significancia.

    Devuelve los campos que pide docs/formato-resultados.md.
    """
    serie = serie.dropna()
    anomalias = quitar_estacionalidad(serie)

    # Tiempo en años decimales, para que la pendiente salga "por año"
    t = serie.index.year + (serie.index.month - 1) / 12

    # Regresión lineal: pendiente e intervalo de confianza del 95 %
    reg = stats.linregress(t, anomalias.values)
    t_crit = stats.t.ppf(1 - alfa / 2, df=len(anomalias) - 2)
    ic = (reg.slope - t_crit * reg.stderr, reg.slope + t_crit * reg.stderr)

    # Mann-Kendall: ¿la tendencia es real o pudo ser casualidad?
    # Nota: los datos mensuales están autocorrelacionados y eso puede exagerar la
    # significancia. Si da tiempo, probar mk.hamed_rao_modification_test.
    prueba = mk.original_test(anomalias.values, alpha=alfa)

    return {
        "pendiente_por_decada": round(float(reg.slope) * 10, 4),
        "ic95": [round(float(ic[0]) * 10, 4), round(float(ic[1]) * 10, 4)],
        "p_valor": float(prueba.p),
        "significativa": bool(prueba.p < alfa),
        "direccion": prueba.trend,  # "increasing", "decreasing" o "no trend"
    }


if __name__ == "__main__":
    # Prueba con datos sintéticos: ciclo anual + calentamiento de 0.3 °C por década + ruido
    rng = np.random.default_rng(42)
    fechas = pd.date_range("1990-01-01", "2025-12-01", freq="MS")
    anios = np.arange(len(fechas)) / 12
    datos = 15 + 5 * np.sin(2 * np.pi * anios) + 0.03 * anios + rng.normal(0, 0.8, len(fechas))
    serie = pd.Series(datos, index=fechas)

    print("Tendencia esperada: +0.30 por década")
    print(analizar_tendencia(serie))
