"""Autenticación con NASA Earthdata Login.

Las credenciales NUNCA se escriben en el código ni se envían al frontend.
earthaccess las busca en este orden (ver docs/07-earthdata.md):

1. Variables de entorno EARTHDATA_USERNAME y EARTHDATA_PASSWORD, o
   EARTHDATA_TOKEN con un token generado en https://urs.earthdata.nasa.gov/
2. El archivo ~/.netrc (en Windows, ~/_netrc).

Este módulo solo valida que exista alguna de esas opciones y muestra mensajes
claros; nunca imprime el usuario, la contraseña ni el token.
"""

from __future__ import annotations

import logging
import netrc
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("atlas.earthdata")
URS_HOST = "urs.earthdata.nasa.gov"


def _netrc_path() -> Path:
    name = "_netrc" if os.name == "nt" else ".netrc"
    return Path(os.environ.get("NETRC", Path.home() / name))


def credentials_source() -> str | None:
    if os.environ.get("EARTHDATA_TOKEN"):
        return "token (EARTHDATA_TOKEN)"
    if os.environ.get("EARTHDATA_USERNAME") and os.environ.get("EARTHDATA_PASSWORD"):
        return "variables de entorno"
    path = _netrc_path()
    if path.is_file():
        try:
            if netrc.netrc(str(path)).authenticators(URS_HOST):
                return f"archivo {path.name}"
        except (netrc.NetrcParseError, OSError):
            logger.warning("No se pudo leer %s; revisa su formato y permisos.", path)
    return None


def basic_credentials() -> tuple[str, str]:
    """Usuario y contraseña para servicios que exigen autenticación básica (AppEEARS)."""
    user, password = os.environ.get("EARTHDATA_USERNAME"), os.environ.get("EARTHDATA_PASSWORD")
    if user and password:
        return user, password
    path = _netrc_path()
    if path.is_file():
        auth = netrc.netrc(str(path)).authenticators(URS_HOST)
        if auth and auth[0] and auth[2]:
            return auth[0], auth[2]
    raise RuntimeError(
        "AppEEARS necesita usuario y contraseña de Earthdata en EARTHDATA_USERNAME/EARTHDATA_PASSWORD "
        f"o en {_netrc_path()}. Ver docs/07-earthdata.md."
    )


def login() -> Any:
    """Inicia sesión con earthaccess usando el entorno o .netrc. Falla con un mensaje claro."""
    source = credentials_source()
    if source is None:
        raise RuntimeError(
            "No se encontraron credenciales de NASA Earthdata. Configura EARTHDATA_USERNAME y "
            "EARTHDATA_PASSWORD en tu .env (o un .netrc). Ver docs/07-earthdata.md."
        )
    import earthaccess

    strategy = "netrc" if source.startswith("archivo") else "environment"
    auth = earthaccess.login(strategy=strategy)
    if not getattr(auth, "authenticated", False):
        raise RuntimeError(
            "Earthdata rechazó las credenciales. Revisa usuario y contraseña en tu .env."
        )
    logger.info("Sesión iniciada en NASA Earthdata (credenciales de: %s).", source)
    return auth
