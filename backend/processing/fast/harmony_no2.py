"""NO₂ (OMNO2d) recortado a México en los servidores de NASA con Harmony.

En lugar de bajar el archivo mundial de cada día (~12 MB) y recortarlo aquí, se le
pide a Harmony (servicio HOSS de NASA, que admite recorte por área para OMNO2d V004)
solo el recuadro de México: ~1 % del tamaño. Se envía una solicitud por año, todas a
la vez, para que NASA las procese en paralelo.

El resultado se guarda en el mismo archivo mensual que la descarga clásica
(data/raw/no2/OMNO2d_<versión>_mexico_AAAA-MM.nc), así que el proceso mensual
(processing/no2/pipeline.process_month) no cambia.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from app.services.dates import days_in_month
from processing.common import qc
from processing.common.paths import MEXICO_BBOX, context
from processing.no2 import pipeline as no2

logger = logging.getLogger("atlas.no2.harmony")
LAT_NAMES = ("lat", "latitude", "ydim")
LON_NAMES = ("lon", "longitude", "xdim")


def _client() -> Any:
    from harmony import Client

    user = os.environ.get("EARTHDATA_USERNAME")
    password = os.environ.get("EARTHDATA_PASSWORD")
    if user and password:
        return Client(auth=(user, password))
    token = os.environ.get("EARTHDATA_TOKEN")
    if token:
        try:
            return Client(token=token)
        except TypeError:
            logger.warning("Esta versión de harmony-py no acepta token; se usará .netrc.")
    return Client()  # usa ~/.netrc (Windows: ~/_netrc)


def _datasets(h5: Any) -> dict[str, Any]:
    found: dict[str, Any] = {}

    def visitor(name: str, obj: Any) -> None:
        if hasattr(obj, "shape"):
            found[name] = obj

    h5.visititems(visitor)
    return found


def _coordinate(datasets: dict[str, Any], names: tuple[str, ...], size: int) -> np.ndarray | None:
    for path, ds in datasets.items():
        base = path.rsplit("/", 1)[-1].lower()
        if base in names and len(ds.shape) == 1 and ds.shape[0] == size:
            return np.asarray(ds[()], dtype="float64")
    return None


def read_subset_file(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Lee un archivo recortado por Harmony: (datos con norte arriba, latitudes, longitudes)."""
    import h5py

    with h5py.File(path, "r") as h5:
        datasets = _datasets(h5)
        field = next((ds for name, ds in datasets.items() if name.endswith(no2.FIELD_SUFFIX)), None)
        if field is None:
            raise KeyError(f"{path.name} no contiene {no2.FIELD_SUFFIX}.")
        data = np.asarray(field[()], dtype="float32")
        if data.ndim == 3:  # algunos recortes conservan una dimensión de tiempo de tamaño 1
            data = data[0]
        ny, nx = data.shape
        lats = _coordinate(datasets, LAT_NAMES, ny)
        lons = _coordinate(datasets, LON_NAMES, nx)
        names = sorted(datasets)

    if lats is None or lons is None:
        raise RuntimeError(
            f"No se encontraron latitudes/longitudes en {path.name} (forma {data.shape}). "
            f"Variables del archivo: {names[:15]}. Envía este mensaje para ajustar el lector."
        )
    data = np.where(qc.omi_valid(data), data, np.nan)
    if lats[0] < lats[-1]:  # sur → norte: se voltea para que el norte quede arriba
        data, lats = data[::-1], lats[::-1]
    west, south, east, north = MEXICO_BBOX
    rows = (lats > south) & (lats < north)
    cols = (lons > west) & (lons < east)
    return data[np.ix_(rows, cols)], lats[rows], lons[cols]


def _months_by_year(start: str, end: str) -> dict[int, list[int]]:
    from processing.fast.plan import months_between

    _, products, _ = context()
    by_year: dict[int, list[int]] = defaultdict(list)
    for year, month in months_between(start, end):
        if products.is_available(no2.VARIABLE, year, month):
            by_year[year].append(month)
    return dict(by_year)


COMPLETE = "_completo.json"
DONE_STATES = ("successful", "complete_with_errors")
PAUSED_STATES = ("paused", "previewing")


def _completed_months(folder: Path) -> set[int]:
    import json

    marker = folder / COMPLETE
    if not marker.is_file():
        return set()
    try:
        return set(json.loads(marker.read_text(encoding="utf-8")).get("months", []))
    except (ValueError, OSError):
        return set()


def _mark_complete(folder: Path, months: list[int], state: str) -> None:
    import json

    done = sorted(_completed_months(folder) | set(months))
    (folder / COMPLETE).write_text(json.dumps({"months": done, "state": state}), encoding="utf-8")


def _submit(client: Any, concept_id: str, year: int, months: list[int]) -> str:
    from harmony import BBox, Collection, Request

    west, south, east, north = MEXICO_BBOX
    first = datetime(year, months[0], 1)
    last = datetime(year, months[-1], days_in_month(year, months[-1]), 23, 59, 59)
    kwargs: dict[str, Any] = {
        "collection": Collection(id=concept_id),
        "spatial": BBox(west, south, east, north),
        "temporal": {"start": first, "stop": last},
    }
    try:  # evita que Harmony pause la solicitud para mostrar una vista previa
        request = Request(**kwargs, skip_preview=True)
    except TypeError:
        request = Request(**kwargs)
    return client.submit(request)


def _wait_until_done(client: Any, job_id: str, year: int) -> str:
    """Espera a que Harmony termine; si pausa la solicitud (lo hace con las grandes), la reanuda."""
    while True:
        client.wait_for_processing(job_id, show_progress=True)
        info = client.status(job_id)
        state = str(info.get("status", "")).lower()
        if state in PAUSED_STATES:
            logger.info("NO₂ %d: Harmony pausó la solicitud; se reanuda automáticamente.", year)
            client.resume(job_id)
            time.sleep(5)
            continue
        if state in DONE_STATES:
            if state == "complete_with_errors":
                logger.warning(
                    "NO₂ %d: Harmony terminó con algunos errores: %s", year, info.get("message")
                )
            return state
        raise RuntimeError(
            f"Harmony terminó la solicitud de {year} con estado «{state}»: {info.get('message')}"
        )


def download(start: str, end: str) -> list[Path]:
    """Descarga con Harmony y arma los archivos mensuales. Devuelve los meses escritos.

    Un año se considera listo solo cuando Harmony terminó por completo (archivo
    _completo.json); si una ejecución anterior quedó a medias, ese año se repite y sus
    meses se reescriben. Los archivos diarios ya descargados se reutilizan.
    """
    paths, products, _ = context()
    product = products.get(no2.VARIABLE)["product"]
    version, concept_id = product["version"], product["concept_id"]
    raw_dir = paths.raw(no2.VARIABLE)
    pending: dict[int, list[int]] = {}
    for year, months in _months_by_year(start, end).items():
        done = _completed_months(raw_dir / "_harmony" / str(year))
        missing = [m for m in months if m not in done]
        if missing:
            pending[year] = missing
    if not pending:
        logger.info("NO₂: todos los meses pedidos ya estaban descargados.")
        return []

    client = _client()
    jobs: dict[int, str] = {}
    for year, months in sorted(pending.items()):
        jobs[year] = _submit(client, concept_id, year, months)
        logger.info("NO₂ %d: solicitud enviada a Harmony (%d meses).", year, len(months))

    written: list[Path] = []
    for year, job_id in sorted(jobs.items()):
        logger.info("NO₂ %d: esperando a que NASA termine el recorte…", year)
        state = _wait_until_done(client, job_id, year)
        folder = raw_dir / "_harmony" / str(year)
        folder.mkdir(parents=True, exist_ok=True)
        files = [Path(f.result()) for f in client.download_all(job_id, directory=str(folder))]
        logger.info("NO₂ %d: %d archivos diarios recortados descargados.", year, len(files))
        all_files = sorted(folder.glob("*.nc4")) or files
        damaged: list[Path] = []
        written += assemble_months(all_files, raw_dir, version, year, pending[year], damaged)
        if damaged:
            logger.warning(
                "NO₂ %d: %d archivos dañados; vuelve a ejecutar el comando para completarlo.",
                year,
                len(damaged),
            )
        else:
            _mark_complete(folder, pending[year], state)
    return written


def assemble_months(
    files: list[Path],
    raw_dir: Path,
    version: str,
    year: int,
    months: list[int],
    damaged: list[Path] | None = None,
) -> list[Path]:
    """Agrupa los archivos diarios por mes (uno por día: si un día se descargó en dos
    solicitudes distintas, se usa el más reciente) y escribe el archivo mensual."""
    by_day: dict[Any, Path] = {}
    for file in sorted(files, key=lambda f: f.stat().st_mtime if f.exists() else 0):
        day = no2._day_from_name(file)
        if day is not None and day.year == year:
            by_day[day] = file
    damaged = [] if damaged is None else damaged
    written = []
    for month in months:
        days, layers = [], []
        lats = lons = None
        for day in sorted(d for d in by_day if d.month == month):
            try:
                sub, lats, lons = read_subset_file(by_day[day])
            except (OSError, KeyError) as exc:
                # Archivo cortado (por ejemplo, si se detuvo el proceso): se borra para
                # que se vuelva a descargar, y el año no se marca como terminado.
                logger.warning("NO₂ %s: archivo dañado (%s); se volverá a descargar.", day, exc)
                by_day[day].unlink(missing_ok=True)
                damaged.append(by_day[day])
                continue
            days.append(np.datetime64(day))
            layers.append(sub)
        if not layers:
            logger.warning(
                "NO₂ %d-%02d: Harmony no devolvió días; el mes queda sin dato.", year, month
            )
            continue
        out = no2.raw_month_path(raw_dir, version, year, month)
        no2.write_month_subset(
            out, days, layers, lats, lons, version, "Recorte a México hecho por NASA Harmony."
        )
        written.append(out)
    return written


def run(start: str, end: str, min_days: int = 3) -> int:
    """Descarga lo que falte y procesa todos los meses disponibles del rango."""
    download(start, end)
    paths, products, _ = context()
    version = products.get(no2.VARIABLE)["product"]["version"]
    done = 0
    for year, months in _months_by_year(start, end).items():
        for month in months:
            if no2.raw_month_path(paths.raw(no2.VARIABLE), version, year, month).exists():
                no2.process_month(year, month, min_days)
                done += 1
    return done
