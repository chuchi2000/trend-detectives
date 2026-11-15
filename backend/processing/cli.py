"""Línea de comandos del procesamiento NASA.

Ejecutar desde la carpeta backend/ con el entorno virtual activo:

    python -m processing.cli verificar-login
    python -m processing.cli precipitacion --inicio 2015-07 --fin 2015-07
    python -m processing.cli no2 --inicio 2015-07 --fin 2015-07
    python -m processing.cli evapotranspiracion --inicio 2015-07 --fin 2015-07
    python -m processing.cli temperatura --inicio 2015-07 --fin 2015-07
    python -m processing.cli comparativo
    python -m processing.cli limites            (descarga del servicio web del INEGI)
    python -m processing.cli catalogo
    python -m processing.cli ee-login
    python -m processing.cli rapido --inicio 2004-01 --fin 2025-12

Por defecto cada variable descarga y luego procesa. Usa --solo-descarga o
--solo-proceso para separar los pasos. Empieza siempre con un mes de prueba.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from app.core.config import load_dotenv_into_environ
from app.core.errors import AtlasError
from app.core.logging import configure_logging
from app.services.dates import parse_ym

ALIASES = {
    "precipitacion": "precipitation",
    "no2": "no2",
    "evapotranspiracion": "evapotranspiration",
    "temperatura": "temperature",
}


def _range(value: str) -> str:
    parse_ym(value)  # valida el formato
    return value


def _variable_command(args: argparse.Namespace) -> None:
    variable = ALIASES[args.command]
    do_download = not args.solo_proceso
    do_process = not args.solo_descarga
    if variable == "precipitation":
        from processing.precipitation import pipeline as pl

        if do_download:
            pl.download(args.inicio, args.fin)
        if do_process:
            pl.process(args.inicio, args.fin)
    elif variable == "no2":
        from processing.no2 import pipeline as pl

        if do_download:
            pl.download(args.inicio, args.fin, keep_global=args.conservar_globales)
        if do_process:
            pl.process(args.inicio, args.fin, min_days=args.min_dias)
    elif variable == "evapotranspiration":
        from processing.evapotranspiration import pipeline as pl

        if do_download:
            pl.download(args.inicio, args.fin)
        if do_process:
            pl.process(args.inicio, args.fin, strict=args.qc_estricto)
    else:
        from processing.temperature import pipeline as pl

        if do_download:
            pl.download(args.inicio, args.fin)
        if do_process:
            pl.process(args.inicio, args.fin)


def main(argv: list[str] | None = None) -> int:
    load_dotenv_into_environ()
    configure_logging("INFO")
    parser = argparse.ArgumentParser(
        prog="python -m processing.cli", description="Procesamiento NASA del Atlas"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("verificar-login", help="Comprueba que las credenciales de Earthdata funcionan")
    for name in ALIASES:
        p = sub.add_parser(name, help=f"Descarga y procesa {name}")
        p.add_argument("--inicio", type=_range, required=True, help="Primer mes, AAAA-MM")
        p.add_argument("--fin", type=_range, required=True, help="Último mes, AAAA-MM")
        group = p.add_mutually_exclusive_group()
        group.add_argument("--solo-descarga", action="store_true")
        group.add_argument("--solo-proceso", action="store_true")
        if name == "no2":
            p.add_argument(
                "--min-dias", type=int, default=3, help="Días válidos mínimos por celda (3)"
            )
            p.add_argument(
                "--conservar-globales",
                action="store_true",
                help="No borrar los archivos diarios globales",
            )
        if name == "evapotranspiracion":
            p.add_argument(
                "--qc-estricto",
                action="store_true",
                help="Descartar píxeles con bit 0 de ET_QC = 1",
            )
    comp = sub.add_parser(
        "comparativo", help="Construye los cubos de 0.25° para comparar variables"
    )
    comp.add_argument("--variables", nargs="*", choices=list(ALIASES.values()))
    comp.add_argument("--zarr", action="store_true", help="Además, exportar cada cubo a Zarr")
    lim = sub.add_parser(
        "limites",
        help="Descarga y prepara los límites estatales y municipales del INEGI",
        description=(
            "Sin opciones, descarga los límites del servicio web del INEGI (necesita internet, "
            "no necesita librerías extra). Con --origen usa shapefiles ya descargados (necesita geopandas)."
        ),
    )
    lim.add_argument(
        "--origen",
        help="Opcional: carpeta con 00ent.shp y 00mun.shp del Marco Geoestadístico",
    )
    lim.add_argument(
        "--tolerancia", type=float, default=0.005, help="Simplificación de estados en grados"
    )
    lim.add_argument(
        "--tolerancia-municipios",
        type=float,
        default=0.002,
        help="Simplificación de municipios en grados (solo servicio web)",
    )
    sub.add_parser("catalogo", help="Muestra lo que ya está procesado")

    sub.add_parser("ee-login", help="Conecta tu cuenta de Google Earth Engine (una sola vez)")
    fast = sub.add_parser(
        "rapido",
        help="Descarga rápida: Earth Engine (precipitación, ET, temperatura) + Harmony (NO₂)",
        description=(
            "Calcula los meses en los servidores de Google y NASA y descarga solo México. "
            "Al final reconstruye la malla comparativa. Ver docs/09-descarga-rapida.md."
        ),
    )
    fast.add_argument("--inicio", type=_range, required=True, help="Primer mes, AAAA-MM")
    fast.add_argument("--fin", type=_range, required=True, help="Último mes, AAAA-MM")
    fast.add_argument(
        "--variables",
        nargs="*",
        choices=list(ALIASES),
        default=list(ALIASES),
        help="Por defecto, las cuatro",
    )
    fast.add_argument(
        "--resolucion-mapa",
        type=float,
        default=0.025,
        help="Malla del mapa para evapotranspiración y temperatura, en grados (0.025 ≈ 2.8 km)",
    )
    fast.add_argument(
        "--hilos", type=int, default=6, help="Meses calculados a la vez en Earth Engine"
    )
    fast.add_argument("--min-dias", type=int, default=3, help="NO₂: días válidos mínimos por celda")
    fast.add_argument(
        "--qc-estricto", action="store_true", help="ET: descartar píxeles con bit 0 de ET_QC = 1"
    )
    fast.add_argument(
        "--forzar", action="store_true", help="Recalcular meses ya hechos en Earth Engine"
    )

    args = parser.parse_args(argv)
    log = logging.getLogger("atlas.cli")
    try:
        if args.command == "verificar-login":
            from processing.common.earthdata import login

            login()
            log.info("Credenciales correctas.")
        elif args.command in ALIASES:
            _variable_command(args)
        elif args.command == "comparativo":
            from processing.comparative import pipeline as comparative

            entries = comparative.build_all(args.variables)
            if args.zarr:
                for entry in entries:
                    comparative.export_zarr(entry.variable)
        elif args.command == "limites":
            from pathlib import Path

            if args.origen:
                from processing.boundaries import pipeline as boundaries

                boundaries.build(Path(args.origen), args.tolerancia)
            else:
                from processing.boundaries import inegi_service

                inegi_service.build(
                    tolerance=args.tolerancia, municipal_tolerance=args.tolerancia_municipios
                )
        elif args.command == "ee-login":
            from processing.fast import earth_engine

            earth_engine.authenticate()
        elif args.command == "rapido":
            from processing.fast import run as fast_run

            fast_run.run_all(
                [ALIASES[v] for v in args.variables],
                args.inicio,
                args.fin,
                map_res=args.resolucion_mapa,
                workers=args.hilos,
                min_days=args.min_dias,
                strict=args.qc_estricto,
                force=args.forzar,
            )
        elif args.command == "catalogo":
            from processing.common.paths import context

            _, _, catalog = context()
            entries = sorted(catalog.entries(), key=lambda e: (e.variable, e.level, e.date or ""))
            if not entries:
                print("El catálogo está vacío: aún no hay datos procesados.")
            for e in entries:
                print(
                    f"{e.variable:<20} {e.level:<12} {e.date or (str(e.start) + '…' + str(e.end)):<17} {e.path}"
                )
    except KeyboardInterrupt:
        log.warning(
            "Detenido por el usuario. Lo que ya terminó quedó guardado; vuelve a ejecutar el "
            "mismo comando para continuar."
        )
        logging.shutdown()
        os._exit(130)  # no esperar a que terminen las descargas que estaban en curso
    except ImportError as exc:
        extra = "processing,rapido" if exc.name in ("ee", "harmony") else "processing"
        log.error('Falta una librería: %s. Instala: pip install -e ".[%s]"', exc.name, extra)
        return 2
    except (AtlasError, RuntimeError, FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
