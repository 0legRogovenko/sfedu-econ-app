"""Календарь недель: таблица 1 семестрового файла → диапазоны дат с типом недели.

4 колонки = 2 пары «диапазон | тип». Читать колонками 0-1, ПОТОМ 2-3: левая пара
непрерывно продолжается правой, построчное чтение перемешает сентябрь с ноябрём.

Календарь импортируется как ДАННЫЕ. Формула «чётная ISO-неделя = верхняя»
сходится на всём корпусе (228/228), но держится на одном учебном годе и сломается
молча на переходе года — поэтому она здесь только ассерт: разошлось → аномалия
админу («источник изменился»), а тип недели всё равно берётся из файла.

Разведка: docs/superpowers/research/2026-07-17-schedule-recon.md, п. 1.8.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from src.models import WeekType
from src.schedule.grid import Grid

# Дефисы двух видов вперемешку в одном файле: '-' (U+002D) и '–' (U+2013).
# Пробелы вокруг плавают, поэтому \s*, а не литерал.
_RANGE = re.compile(
    r"^(\d\d)\.(\d\d)\.(\d\d)\s*[-–]\s*(\d\d)\.(\d\d)\.(\d\d)$"
)

_WEEK_TYPES = {
    "верхняя неделя": WeekType.UPPER,
    "нижняя неделя": WeekType.LOWER,
}


@dataclass(frozen=True)
class WeekRange:
    """Одна неделя семестра.

    raw — исходный текст ячейки диапазона: нужен админу, когда он разбирается,
    почему неделя выглядит не так.
    """

    date_from: date
    date_to: date
    week_type: WeekType
    raw: str


@dataclass(frozen=True)
class CalendarAnomaly:
    """Строка календаря, которую разобрать не удалось либо которая разошлась
    с ISO-чётностью. Уходит в UnparsedCell → очередь админа; reason влезает
    в UnparsedCell.reason (String(200))."""

    reason: str
    raw_text: str


@dataclass(frozen=True)
class WeekCalendarParse:
    weeks: tuple[WeekRange, ...]
    anomalies: tuple[CalendarAnomaly, ...]


def iso_parity_week_type(day: date) -> WeekType:
    """Формула ЮФУ: чётная ISO-неделя — верхняя, нечётная — нижняя.

    Только для ассерта. Источник истины — календарь из файла: чётность считается
    по ISO-году, и на переходе года формула поедет молча (29.12.25 — уже ISO-неделя
    1 следующего года).
    """
    return WeekType.UPPER if day.isocalendar()[1] % 2 == 0 else WeekType.LOWER


def is_week_calendar(grid: Grid) -> bool:
    """Похожа ли таблица на календарь недель.

    Нужна, чтобы importer выбирал таблицу по содержимому, а не по номеру: если
    ЮФУ вставит таблицу перед календарём, «таблица 1» молча станет чужой.
    """
    if grid.n_cols < 2 or grid.n_cols % 2 or grid.n_rows == 0:
        return False
    first_range = grid.cell_at(0, 0)
    first_type = grid.cell_at(0, 1)
    if first_range is None or first_type is None:
        return False
    return bool(
        _RANGE.match(_flat(first_range.text))
        and _flat(first_type.text).lower() in _WEEK_TYPES
    )


def parse_week_calendar(grid: Grid) -> WeekCalendarParse:
    """Календарь недель из таблицы 1 семестрового файла.

    Ничего не теряем молча: каждая непустая строка либо становится WeekRange,
    либо попадает в anomalies. Не падаем: испорченная строка не уносит с собой
    остальные — админ увидит и её, и разобранный календарь.
    """
    weeks: list[WeekRange] = []
    anomalies: list[CalendarAnomaly] = []

    for range_col in range(0, grid.n_cols, 2):
        for row in range(grid.n_rows):
            range_cell = grid.cell_at(row, range_col)
            type_cell = grid.cell_at(row, range_col + 1)
            if range_cell is None or type_cell is None:
                continue

            range_text = _flat(range_cell.text)
            type_text = _flat(type_cell.text)
            if not range_text and not type_text:
                continue  # хвост таблицы, а не потеря данных

            raw = f"{range_text} | {type_text}"
            match = _RANGE.match(range_text)
            week_type = _WEEK_TYPES.get(type_text.lower())
            if match is None or week_type is None:
                anomalies.append(
                    CalendarAnomaly(
                        reason="календарь недель: строка не разобрана",
                        raw_text=raw,
                    )
                )
                continue

            date_from = _date(match.group(1), match.group(2), match.group(3))
            date_to = _date(match.group(4), match.group(5), match.group(6))
            if iso_parity_week_type(date_from) is not week_type:
                # Верим файлу, не формуле: неделя всё равно попадёт в календарь.
                anomalies.append(
                    CalendarAnomaly(
                        reason=(
                            "календарь недель: тип разошёлся с ISO-чётностью — "
                            "структура источника изменилась"
                        ),
                        raw_text=raw,
                    )
                )
            weeks.append(
                WeekRange(
                    date_from=date_from,
                    date_to=date_to,
                    week_type=week_type,
                    raw=range_cell.text,
                )
            )

    return WeekCalendarParse(weeks=tuple(weeks), anomalies=tuple(anomalies))


def _flat(text: str) -> str:
    """Схлопнуть переносы и двойные пробелы: в PDF диапазон рвётся по строкам."""
    return re.sub(r"\s+", " ", text).strip()


def _date(day: str, month: str, year: str) -> date:
    # Год двузначный всюду в корпусе: '25' → 2025, '26' → 2026.
    return date(2000 + int(year), int(month), int(day))
