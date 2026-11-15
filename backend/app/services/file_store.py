"""Fuente de DATOS REALES: archivos procesados de NASA registrados en el catálogo.

- Mapa: COG mensual en resolución nativa, servido como teselas por TiTiler.
  El navegador nunca descarga el NetCDF ni el COG completo, solo teselas PNG.
- Consulta por punto: se lee el COG nativo con rasterio (un solo píxel).
- Series, estadísticas y correlaciones: cubo de la malla común de 0.25°
  (Zarr o NetCDF) abierto con xarray de forma perezosa.

Las librerías geoespaciales se importan dentro de las funciones para que la API
pueda arrancar en modo DEMO sin tenerlas instaladas.
"""

from __future__ import annotations

from typing import Any, Literal
from urllib.parse import quote

import numpy as np

from app.core.config import Settings
from app.core.errors import AtlasError, NotProcessed
from app.services.catalog import Catalog, CatalogEntry
from app.services.colormaps import interval_colormap_param
from app.services.dates import format_ym, human_ym, parse_ym, ym_index
from app.services.grid import CommonGrid
from app.services.products import ProductCatalog
from app.services.regions import RegionService


class MissingGeoLibraries(AtlasError):
    status_code = 503
    code = "faltan_librerias_geoespaciales"


def _require(module: str) -> Any:
    try:
        return __import__(module)
    except ImportError as exc:
        raise MissingGeoLibraries(
            f"El modo DATOS REALES necesita '{module}'. Instala: pip install -e \".[geo]\""
        ) from exc


class FileStore:
    mode: Literal["demo", "real"] = "real"

    def __init__(
        self,
        settings: Settings,
        products: ProductCatalog,
        grid: CommonGrid,
        catalog: Catalog,
        regions: RegionService,
    ) -> None:
        self.settings = settings
        self.products = products
        self.grid = grid
        self.catalog = catalog
        self.regions = regions
        self._datasets: dict[str, Any] = {}

    # -- utilidades ---------------------------------------------------------
    def _native_entry(self, variable: str, year: int, month: int) -> CatalogEntry:
        self.products.require_available(variable, year, month)
        self.catalog.refresh_if_changed()
        date = format_ym(year, month)
        entry = self.catalog.find(variable, "native", date)
        if entry is None:
            name = self.products.get(variable)["name"]
            raise NotProcessed(
                f"{name} de {human_ym(date)} todavía no se ha descargado ni procesado. "
                f"Ejecuta: python -m processing.cli {variable} --inicio {date} --fin {date}"
            )
        return entry

    def _comparative(self, variable: str) -> Any:
        self.catalog.refresh_if_changed()
        entry = self.catalog.find(variable, "comparative", None)
        if entry is None:
            raise NotProcessed(
                "Aún no existe el cubo comparativo de 0.25°. Ejecuta: python -m processing.cli comparativo"
            )
        if variable not in self._datasets:
            xr = _require("xarray")
            path = self.settings.data_dir / entry.path
            if entry.format == "zarr":
                ds = xr.open_zarr(path)
            else:
                ds = xr.open_dataset(path)
            self._datasets[variable] = ds
        return self._datasets[variable]

    # -- interfaz DataStore -------------------------------------------------
    def national_mask(self) -> np.ndarray:
        mask = self.regions.national_mask()
        if mask is None:
            # Sin límites del INEGI: se usa toda la malla (los océanos ya son NaN en los datos).
            return np.ones(self.grid.shape, dtype=bool)
        return mask

    def processed_months(self, variable: str) -> list[str] | None:
        self.catalog.refresh_if_changed()
        return self.catalog.processed_months(variable)

    def field(self, variable: str, year: int, month: int) -> np.ndarray:
        self.products.require_available(variable, year, month)
        ds = self._comparative(variable)
        date = format_ym(year, month)
        try:
            data = ds[variable].sel(time=date).values
        except KeyError as exc:
            raise NotProcessed(f"El cubo comparativo no contiene {human_ym(date)}.") from exc
        return np.asarray(data, dtype="float32").reshape(self.grid.shape)

    def cube(self, variable: str, start: str, end: str) -> tuple[list[str], np.ndarray]:
        ds = self._comparative(variable)
        avail_start, avail_end = self.products.availability(variable)
        i0 = max(ym_index(*parse_ym(start)), ym_index(*parse_ym(avail_start)))
        i1 = min(ym_index(*parse_ym(end)), ym_index(*parse_ym(avail_end)))
        if i0 > i1:
            return [], np.empty((0, *self.grid.shape), dtype="float32")
        sub = ds[variable].sel(
            time=slice(format_ym(i0 // 12, i0 % 12 + 1), format_ym(i1 // 12, i1 % 12 + 1))
        )
        times = [str(t)[:7] for t in sub["time"].values.astype("datetime64[M]")]
        return times, np.asarray(sub.values, dtype="float32")

    def map_layer(self, variable: str, year: int, month: int) -> dict[str, Any]:
        entry = self._native_entry(variable, year, month)
        display = self.products.get(variable)["display"]
        cog_url = f"{self.settings.titiler_data_dir}/{entry.path}"
        colormap = quote(interval_colormap_param(display))
        tile = (
            f"{self.settings.titiler_url}/cog/tiles/WebMercatorQuad/{{z}}/{{x}}/{{y}}.png"
            f"?url={quote(cog_url)}&bidx=1&colormap={colormap}"
        )
        product = self.products.get(variable)["product"]
        return {
            "layer": {
                "kind": "tiles",
                "tiles": [tile],
                "tile_size": 256,
                "bounds": [self.grid.west, self.grid.south, self.grid.east, self.grid.north],
                "attribution": f"NASA {product['provider']} · {product['short_name']} v{product['version']}",
            },
            "resolution": self.products.get(variable)["spatial"]["native_resolution"],
            "quality": {
                "coverage": entry.coverage,
                "n_valid": entry.n_valid,
                "flags": list(entry.quality.get("flags", [])),
                "notes": list(entry.quality.get("notes", [])),
                "details": {k: v for k, v in entry.quality.items() if k not in {"flags", "notes"}},
            },
        }

    def point_value(
        self, variable: str, year: int, month: int, lat: float, lon: float
    ) -> dict[str, Any]:
        entry = self._native_entry(variable, year, month)
        rasterio = _require("rasterio")
        path = self.settings.data_dir / entry.path
        with rasterio.open(path) as src:
            row, col = src.index(lon, lat)
            if not (0 <= row < src.height and 0 <= col < src.width):
                return {
                    "value": None,
                    "cell": None,
                    "resolution": entry.quality.get("resolution", ""),
                }
            window = rasterio.windows.Window(col, row, 1, 1)
            value = src.read(1, window=window, masked=True)[0, 0]
            x, y = src.xy(row, col)
            res = abs(src.res[0])
        valid = value is not np.ma.masked and np.isfinite(float(value))
        return {
            "value": float(value) if valid else None,
            "cell": {"lat": float(y), "lon": float(x), "res": float(res)},
            "resolution": self.products.get(variable)["spatial"]["native_resolution"],
        }

    def raster_path(self, variable: str, year: int, month: int) -> str:
        return str(self.settings.data_dir / self._native_entry(variable, year, month).path)
