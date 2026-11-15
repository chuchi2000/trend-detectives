"""Orquestador del modo rápido: NO₂ con Harmony y las otras tres variables con Earth
Engine, al mismo tiempo; al final, la malla comparativa de 0.25°."""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger("atlas.rapido")
EE_SET = ("precipitation", "evapotranspiration", "temperature")


def run_all(
    variables: list[str],
    start: str,
    end: str,
    map_res: float = 0.025,
    workers: int = 6,
    min_days: int = 3,
    strict: bool = False,
    force: bool = False,
) -> None:
    import importlib

    needed = ["xarray", "rasterio", "h5py"]
    if "no2" in variables:
        needed.append("harmony")
    if any(v in EE_SET for v in variables):
        needed.append("ee")
    for module in needed:
        importlib.import_module(module)  # ImportError → la CLI dice qué instalar

    began = time.monotonic()
    results: dict[str, str] = {}

    def no2_job() -> None:
        from processing.fast import harmony_no2

        try:
            done = harmony_no2.run(start, end, min_days=min_days)
            results["no2"] = f"{done} meses procesados"
        except Exception as exc:  # noqa: BLE001 - se informa al final
            logger.exception("NO₂ con Harmony falló")
            results["no2"] = f"ERROR: {exc}"

    thread = None
    if "no2" in variables:
        thread = threading.Thread(target=no2_job, name="no2-harmony", daemon=True)
        thread.start()

    ee_vars = [v for v in variables if v in EE_SET]
    if ee_vars:
        from processing.fast import earth_engine

        try:
            done = earth_engine.run(
                ee_vars, start, end, map_res=map_res, workers=workers, force=force, strict=strict
            )
            results["earth_engine"] = f"{done} meses calculados ({', '.join(ee_vars)})"
        except Exception as exc:  # noqa: BLE001 - se informa al final
            logger.exception("Earth Engine falló")
            results["earth_engine"] = f"ERROR: {exc}"

    while thread is not None and thread.is_alive():
        thread.join(timeout=1.0)  # en pasos cortos para que Ctrl + C funcione en Windows

    from processing.comparative import pipeline as comparative

    comparative.build_all(variables)
    minutes = (time.monotonic() - began) / 60
    logger.info("Modo rápido terminado en %.0f min.", minutes)
    for part, text in results.items():
        logger.info("  %s: %s", part, text)
