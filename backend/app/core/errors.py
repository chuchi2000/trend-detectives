"""Errores del dominio.

Los servicios lanzan estas excepciones; la capa HTTP (FastAPI) las convierte en
respuestas JSON con la forma {"error": {"code": ..., "message": ...}}.
Así los servicios no dependen del framework web y se pueden probar solos.
"""

from __future__ import annotations


class AtlasError(Exception):
    status_code = 400
    code = "solicitud_invalida"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "message": self.message}}


class InvalidRequest(AtlasError):
    status_code = 422
    code = "parametro_invalido"


class NotFound(AtlasError):
    status_code = 404
    code = "no_encontrado"


class DateUnavailable(AtlasError):
    """La variable no tiene datos válidos para esa fecha (disponibilidad del producto)."""

    status_code = 404
    code = "fecha_sin_datos"


class NotProcessed(AtlasError):
    """La fecha está dentro de la disponibilidad del producto, pero aún no se ha procesado."""

    status_code = 404
    code = "sin_procesar"


class NotAvailableInMode(AtlasError):
    status_code = 409
    code = "no_disponible_en_este_modo"
