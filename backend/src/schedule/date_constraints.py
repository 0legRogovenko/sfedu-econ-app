"""Resolve lesson date prefixes into exact inclusive visibility windows.

Schedule cells contain both ranges (``До 17.12``, ``С 28.04 по 26.05``)
and sparse lists (``08.11, 15.11``).  Sparse dates are returned separately so
the client does not turn the gap between them into invented lessons.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

_DATE = re.compile(r"(\d\d?)\.(\d\d)")


@dataclass(frozen=True)
class ResolvedDates:
    """Inclusive bounds plus an optional exact set of dates."""

    valid_from: date | None
    valid_to: date | None
    specific_dates: tuple[date, ...] = ()


def _distance_to_window(value: date, valid_from: date, valid_to: date) -> int:
    if value < valid_from:
        return (valid_from - value).days
    if value > valid_to:
        return (value - valid_to).days
    return 0


def _resolve_date(
    day: int,
    month: int,
    valid_from: date,
    valid_to: date,
) -> date | None:
    """Choose the closest year, including semesters that cross New Year."""
    candidates: list[date] = []
    for year in range(valid_from.year - 1, valid_to.year + 2):
        try:
            candidates.append(date(year, month, day))
        except ValueError:
            continue
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda value: (
            _distance_to_window(value, valid_from, valid_to),
            abs((value - valid_from).days),
            value,
        ),
    )


def _resolved_values(
    raw: str,
    valid_from: date,
    valid_to: date,
) -> tuple[date, ...]:
    values: list[date] = []
    for day_raw, month_raw in _DATE.findall(raw):
        value = _resolve_date(int(day_raw), int(month_raw), valid_from, valid_to)
        if value is None:
            return ()
        values.append(value)
    return tuple(values)


def _window(
    valid_from: date,
    valid_to: date,
    lower: date | None = None,
    upper: date | None = None,
) -> ResolvedDates | None:
    start = max(valid_from, lower) if lower is not None else valid_from
    end = min(valid_to, upper) if upper is not None else valid_to
    if start > end:
        return None
    return ResolvedDates(start, end)


def resolve_date_constraint(
    raw: str | None,
    valid_from: date | None,
    valid_to: date | None,
) -> ResolvedDates | None:
    """Narrow a base period using a date prefix from a schedule cell."""
    if raw is None:
        return ResolvedDates(valid_from, valid_to)
    if valid_from is None or valid_to is None or valid_from > valid_to:
        return None

    values = _resolved_values(raw, valid_from, valid_to)
    if not values:
        return None

    lowered = raw.strip().casefold()
    if lowered.startswith("с") and " по " in lowered and len(values) == 2:
        return _window(valid_from, valid_to, values[0], values[1])
    if lowered.startswith(("до", "по")) and len(values) == 1:
        return _window(valid_from, valid_to, upper=values[0])
    if lowered.startswith("с") and len(values) == 1:
        return _window(valid_from, valid_to, lower=values[0])

    exact = tuple(
        sorted({value for value in values if valid_from <= value <= valid_to})
    )
    if not exact:
        return None
    return ResolvedDates(exact[0], exact[-1], exact)
