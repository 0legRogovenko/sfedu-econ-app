"""Связывание людей справочника с парами и экзаменами расписания.

ПОЧЕМУ НЕ ЧЕРЕЗ ТАБЛИЦУ `teachers`. Импортёр кладёт в неё только ПЕРВОГО
преподавателя ячейки. Проверено на живой базе: у Погореловой Т.Г. ноль строк
в `teachers` при 18 парах — связывание через неё сказало бы студенту «пар
нет», а это утверждение факта, и оно ложное. Поэтому источником служит сырой
текст ячейки `Lesson.cell_raw` и `ExamEvent.teacher`.

ДВЕ ЗАЩИТЫ, БЕЗ КОТОРЫХ ЛИНКЕР ВРЕДЕН:

1. Фильтр по реестру. `extract.find_names` честно находит кандидатов в мусоре:
   «Дисциплины ВПК» → «Дисциплины В.П.», «Свиридов АСУ» → «Свиридов А.С.»
   (а это РЕАЛЬНЫЙ чужой человек), «В.Н.»/«Н.Н.» — маркеры верхней и нижней
   недели, формой неотличимые от инициалов. Связью считается только ключ,
   который есть в реестре людей.

2. Сегментация по предметам. В 28 ячейках корпуса несколько предметов И
   несколько преподавателей сразу. Без разрезания текста по позициям
   предметов преподаватель одного предмета получает пары другого — ровно та
   ошибка, из-за которой студент открыл бы чужое расписание.

СРАВНЕНИЕ ТОЛЬКО ТОЧНОЕ: фамилия и ОБА инициала. Никакого Левенштейна.
В данных живут Ласкова Т.С. и Ласкова Д.С. — Татьяна Сергеевна и Дарья
Сергеевна, два разных человека, расстояние в один символ; любой матчер с
порогом «одна правка» их склеит.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field

from src.persons.extract import collapse_spaces, find_name_spans
from src.persons.names import key_of_full, person_key


@dataclass
class Registry:
    """Реестр людей справочника: ключ → список исходных записей контактов."""

    by_key: dict[tuple, list] = field(default_factory=dict)

    def add(self, contact) -> bool:
        """Добавляет контакт. False — ФИО не разобралось (человек без связи)."""
        key = key_of_full(contact.name)
        if key is None:
            return False
        self.by_key.setdefault(key, []).append(contact)
        return True

    def __contains__(self, key: tuple) -> bool:
        return key in self.by_key


def build_registry(contacts: Iterable) -> tuple[Registry, list]:
    """Реестр + список контактов, ФИО которых не разобралось."""
    registry = Registry()
    unparsed = [c for c in contacts if not registry.add(c)]
    return registry, unparsed


def _keys_in(text: str, registry: Registry) -> set[tuple]:
    """Ключи людей реестра, упомянутых в тексте."""
    found = set()
    for _, _, (surname, given, patronymic) in find_name_spans(text or ""):
        key = person_key(surname, given, patronymic)
        if key in registry:
            found.add(key)
    return found


def link_cell(cell_raw: str, lessons: list, registry: Registry) -> dict:
    """Пары одной ячейки → ключи людей.

    Ячейка может содержать несколько предметов. Тогда текст режется по
    позициям названий предметов, и каждой паре достаются только те имена,
    что стоят в её отрезке.
    """
    text = collapse_spaces(cell_raw or "")
    subjects = {lesson.subject for lesson in lessons}

    if len(subjects) <= 1:
        keys = _keys_in(text, registry)
        return {lesson.id: set(keys) for lesson in lessons}

    # Позиция каждого предмета в тексте ячейки.
    positions: dict[str, int] = {}
    for subject in subjects:
        positions[subject] = text.find(collapse_spaces(subject))

    if any(position < 0 for position in positions.values()):
        # Название предмета в сыром тексте не нашлось — резать наугад нельзя,
        # это и есть путь к чужому расписанию. Лучше не связать вовсе.
        return {lesson.id: set() for lesson in lessons}

    ordered = sorted(positions.items(), key=lambda item: item[1])
    bounds: dict[str, tuple[int, int]] = {}
    for index, (subject, start) in enumerate(ordered):
        end = ordered[index + 1][1] if index + 1 < len(ordered) else len(text)
        bounds[subject] = (start, end)

    result: dict[int, set] = {}
    for lesson in lessons:
        start, end = bounds[lesson.subject]
        result[lesson.id] = _keys_in(text[start:end], registry)
    return result


def link_lessons(lessons: Iterable, registry: Registry) -> dict[int, set]:
    """Все пары → ключи людей. Группировка по ячейке для сегментации."""
    by_cell: dict[str, list] = {}
    for lesson in lessons:
        by_cell.setdefault(lesson.cell_raw or "", []).append(lesson)

    links: dict[int, set] = {}
    for cell_raw, cell_lessons in by_cell.items():
        links.update(link_cell(cell_raw, cell_lessons, registry))
    return links


def link_exams(exams: Iterable, registry: Registry) -> dict[int, set]:
    """Экзамены → ключи людей. Сегментация не нужна: одна запись — один предмет."""
    return {exam.id: _keys_in(exam.teacher or "", registry) for exam in exams}
