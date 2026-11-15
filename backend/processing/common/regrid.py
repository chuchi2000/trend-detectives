"""Agregación conservativa a la malla común de 0.25°.

Para pasar de una malla fina (0.1°, 1 km, 500 m) a 0.25° se calcula, para
cada celda de destino, el promedio de las celdas de origen ponderado por el
área que comparten. No se inventa detalle: una malla más gruesa nunca se
sobremuestrea.

- El área en latitud se mide con sin(φ), que es proporcional al área real
  sobre la esfera; en longitud, con grados.
- Se ignoran los NaN. Una celda de destino necesita al menos
  `min_valid_fraction` de su área cubierta con datos válidos.
- Como la malla es rectilínea, los pesos se separan en una matriz de latitud y
  otra de longitud: resultado = W_lat · datos · W_lonᵀ.
"""

from __future__ import annotations

import numpy as np


def edges_from_centers(centers: np.ndarray) -> np.ndarray:
    centers = np.asarray(centers, dtype="float64")
    step = np.diff(centers)
    if not np.allclose(step, step[0], rtol=1e-4, atol=1e-9):
        raise ValueError("La malla de origen no es regular.")
    half = step[0] / 2
    return np.concatenate([centers - half, [centers[-1] + half]])


def overlap_matrix(src_edges: np.ndarray, dst_edges: np.ndarray) -> np.ndarray:
    """Longitud de traslape [n_dst, n_src] entre intervalos (bordes en cualquier orden)."""
    s_lo = np.minimum(src_edges[:-1], src_edges[1:])
    s_hi = np.maximum(src_edges[:-1], src_edges[1:])
    d_lo = np.minimum(dst_edges[:-1], dst_edges[1:])
    d_hi = np.maximum(dst_edges[:-1], dst_edges[1:])
    lo = np.maximum(d_lo[:, None], s_lo[None, :])
    hi = np.minimum(d_hi[:, None], s_hi[None, :])
    return np.clip(hi - lo, 0.0, None)


def conservative_regrid(
    data: np.ndarray,
    src_lat_edges: np.ndarray,
    src_lon_edges: np.ndarray,
    dst_lat_edges: np.ndarray,
    dst_lon_edges: np.ndarray,
    min_valid_fraction: float = 0.5,
    row_block: int = 1024,
) -> tuple[np.ndarray, np.ndarray]:
    """Devuelve (campo_regrillado, fracción_válida) en la malla de destino."""
    sin_src = np.sin(np.deg2rad(np.asarray(src_lat_edges, dtype="float64")))
    sin_dst = np.sin(np.deg2rad(np.asarray(dst_lat_edges, dtype="float64")))
    w_lat = overlap_matrix(sin_src, sin_dst)
    w_lon = overlap_matrix(
        np.asarray(src_lon_edges, "float64"), np.asarray(dst_lon_edges, "float64")
    )

    num = np.zeros((w_lat.shape[0], w_lon.shape[0]))
    den = np.zeros_like(num)
    for r0 in range(0, data.shape[0], row_block):
        block = np.asarray(data[r0 : r0 + row_block], dtype="float64")
        valid = np.isfinite(block)
        wl = w_lat[:, r0 : r0 + row_block]
        num += wl @ np.where(valid, block, 0.0) @ w_lon.T
        den += wl @ valid.astype("float64") @ w_lon.T

    dst_area = np.abs(np.diff(sin_dst))[:, None] * np.abs(np.diff(dst_lon_edges))[None, :]
    fraction = den / dst_area
    with np.errstate(divide="ignore", invalid="ignore"):
        result = num / den
    result = np.where(fraction >= min_valid_fraction, result, np.nan)
    return result.astype("float32"), fraction.astype("float32")
