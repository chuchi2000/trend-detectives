"""Utilidades de fechas mensuales.

Un mes se representa como texto "AAAA-MM" o como índice entero
(año × 12 + mes − 1). El índice permite comparar y recorrer meses fácilmente.
"""

from __future__ import annotations

import calendar
from collections.abc import Iterator

from app.core.i18n import get_lang, tr

MONTH_NAMES_ES = [
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
]
MONTH_NAMES_EN = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def ym_index(year: int, month: int) -> int:
    return year * 12 + (month - 1)


def from_index(index: int) -> tuple[int, int]:
    return index // 12, index % 12 + 1


def parse_ym(text: str) -> tuple[int, int]:
    try:
        year_s, month_s = text.split("-")
        year, month = int(year_s), int(month_s)
    except ValueError as exc:  # formato incorrecto
        raise ValueError(
            tr(
                f"Fecha '{text}' inválida; usa el formato AAAA-MM.",
                f"Invalid date '{text}'; use the YYYY-MM format.",
            )
        ) from exc
    if not 1 <= month <= 12:
        raise ValueError(
            tr(f"Mes {month} fuera de rango (1–12).", f"Month {month} out of range (1–12).")
        )
    return year, month


def format_ym(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


def human_ym(text: str) -> str:
    year, month = parse_ym(text)
    if get_lang() == "en":
        return f"{MONTH_NAMES_EN[month - 1]} {year}"
    return f"{MONTH_NAMES_ES[month - 1]} de {year}"


def days_in_month(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def iter_months(start: str, end: str) -> Iterator[tuple[int, int]]:
    i0 = ym_index(*parse_ym(start))
    i1 = ym_index(*parse_ym(end))
    for i in range(i0, i1 + 1):
        yield from_index(i)
