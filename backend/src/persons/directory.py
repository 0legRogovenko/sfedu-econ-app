"""Единый справочник людей: контакты + преподаватели расписания в одном списке.

Раньше в приложении было ДВА поиска — по справочнику контактов и отдельно по
преподавателям для просмотра расписания. Здесь они сводятся в один список
людей. Человек может прийти:
- только из контактов (администратор деканата — расписания нет по должности);
- только из расписания (общевузовский преподаватель — контакта на сайте
  экономфака нет и не будет: Груданова И.Ю. — 151 пара);
- из обоих источников (преподаватель кафедры).

Ключ человека — фамилия + оба инициала (см. persons.names.person_key). Всё
связывание идёт через него; строку `teachers` как источник истины НЕ
используем (импортёр кладёт туда только первого преподавателя ячейки).
"""

from __future__ import annotations

import base64
from collections.abc import Iterable
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from src.models import Contact, DirectoryOverride, ExamEvent, Lesson, Teacher
from src.persons.extract import find_names
from src.persons.linker import Registry, build_registry, link_exams, link_lessons
from src.persons.names import parse_person, person_key, short_name

_ID_SEP = "\x1f"  # разделитель внутри ключа, в ФИО не встречается
_DEANERY = "Деканат"  # у человека с несколькими секциями показываем как главную


def encode_id(key: tuple[str, str, str]) -> str:
    """Ключ человека → строковый id для URL (устойчивый между перезапусками)."""
    raw = _ID_SEP.join(key).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_id(person_id: str) -> tuple[str, str, str] | None:
    """id из URL → ключ. None, если id битый (не роняем 500 на кривой ввод)."""
    try:
        padding = "=" * (-len(person_id) % 4)
        raw = base64.urlsafe_b64decode(person_id + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    parts = raw.split(_ID_SEP)
    return tuple(parts) if len(parts) == 3 else None  # type: ignore[return-value]


@dataclass
class PersonRow:
    key: tuple[str, str, str]
    short_name: str          # «Фамилия И.О.» — для списка и поиска
    full_name: str           # «Фамилия Имя Отчество» — для карточки
    sections: list[str] = field(default_factory=list)  # деканат / кафедры
    roles: list[str] = field(default_factory=list)
    email: str | None = None
    lesson_count: int = 0
    exam_count: int = 0

    @property
    def id(self) -> str:
        return encode_id(self.key)

    @property
    def has_schedule(self) -> bool:
        return self.lesson_count > 0 or self.exam_count > 0


def _lesson_key_counts(links: dict[int, set]) -> dict[tuple, int]:
    counts: dict[tuple, int] = {}
    for keys in links.values():
        for key in keys:
            counts[key] = counts.get(key, 0) + 1
    return counts


def _teacher_keys(db: Session) -> set[tuple]:
    """Ключи людей из таблицы `teachers` — whitelist ВНЕШНИХ преподавателей.

    Контакты покрывают только экономфак; общевузовские преподаватели
    (Груданова И.Ю. — 151 пара) контакта не имеют. Их допускает в реестр
    таблица `teachers`: импортёр наполнил её проверенными именами, мусора
    вроде «Дисциплины В.П.» там нет. Сдвоенные ячейки («Бутова С.В. /
    Писанка С.А.») дают два ключа — их и разбирает find_names.
    """
    keys: set[tuple] = set()
    for teacher in db.scalars(select(Teacher)):
        for surname, gi, pi in find_names(teacher.full_name or ""):
            keys.add(person_key(surname, gi, pi))
    return keys


def build_directory(db: Session) -> list[PersonRow]:
    """Единый список людей, отсортированный по короткому имени."""
    contacts = db.scalars(select(Contact)).all()
    registry, _ = build_registry(contacts)

    # Реестр = контакты ∪ преподаватели: без второго whitelist внешние
    # преподаватели выпали бы из справочника (их имена не в контактах, а
    # пропускать в реестр ЛЮБОЕ имя из ячейки нельзя — вернётся мусор).
    teacher_keys = _teacher_keys(db)
    for key in teacher_keys:
        registry.by_key.setdefault(key, [])

    lessons = db.scalars(select(Lesson)).all()
    exams = db.scalars(select(ExamEvent)).all()
    lesson_counts = _lesson_key_counts(link_lessons(lessons, registry))
    exam_counts = _lesson_key_counts(link_exams(exams, registry))

    people: dict[tuple, PersonRow] = {}

    # 1) Люди из справочника контактов (дедуп по ключу: один человек может
    #    быть заведён и в деканате, и на кафедре — это одна карточка, две роли).
    for contact in contacts:
        parsed = parse_person(contact.name)
        if parsed is None:
            continue
        surname, given, patronymic = parsed
        key = person_key(surname, given[:1], patronymic[:1])
        row = people.get(key)
        if row is None:
            row = PersonRow(
                key=key,
                short_name=short_name(contact.name),
                full_name=f"{surname} {given} {patronymic}",
                email=contact.email,
                lesson_count=lesson_counts.get(key, 0),
                exam_count=exam_counts.get(key, 0),
            )
            people[key] = row
        if contact.section and contact.section not in row.sections:
            row.sections.append(contact.section)
        if contact.role and contact.role not in row.roles:
            row.roles.append(contact.role)
        # Почта: берём первую непустую (у дублей она одинаковая — это и есть
        # признак, по которому их признали одним человеком).
        row.email = row.email or contact.email

    # 2) Люди ТОЛЬКО из расписания (внешние преподаватели): у них нет контакта,
    #    полного ФИО тоже нет — короткое имя и есть всё, что мы знаем.
    known = set(people)
    for key, count in {**lesson_counts, **exam_counts}.items():
        if key in known:
            continue
        surname, gi, pi = key
        display = f"{surname.capitalize()} {gi.upper()}.{pi.upper()}."
        people[key] = PersonRow(
            key=key,
            short_name=display,
            full_name=display,
            lesson_count=lesson_counts.get(key, 0),
            exam_count=exam_counts.get(key, 0),
        )

    for row in people.values():
        # Деканат — «головная» принадлежность: замдекана, читающий на кафедре,
        # в справочнике должен стоять в деканате. Клиент группирует по первой
        # секции, поэтому порядок задаём здесь.
        if _DEANERY in row.sections:
            row.sections = [_DEANERY] + [s for s in row.sections if s != _DEANERY]

    _apply_overrides(db, people)
    return sorted(people.values(), key=lambda p: p.short_name.lower())


def _override_key(match_name: str) -> tuple | None:
    """Короткое «Фамилия И.О.» из правки → тот же ключ, что у человека."""
    names = find_names(match_name)
    return person_key(*names[0]) if names else None


def _apply_overrides(db: Session, people: dict[tuple, PersonRow]) -> None:
    """Ручные правки поверх автозабора: пин почты и скрытие людей."""
    for override in db.scalars(select(DirectoryOverride)):
        key = _override_key(override.match_name)
        if key is None:
            continue
        if override.hidden:
            people.pop(key, None)
            continue
        row = people.get(key)
        if row is not None and override.email:
            row.email = override.email


def lessons_for_person(db: Session, key: tuple[str, str, str]) -> list[Lesson]:
    """Все пары, связанные с этим человеком — через текст ячейки, не teacher_id.

    Ради этого весь модуль и существует: у Погореловой Т.Г. нет строки в
    `teachers`, а пар 18 — фильтр по teacher_id их бы потерял.
    """
    # Мини-реестр из одного ключа: линкер ищет только этого человека, но
    # сегментацию по предметам делает по всем парам ячейки — поэтому чужие
    # пары многопредметной ячейки к нему не прилипнут.
    registry = Registry(by_key={key: []})
    # joinedload(teacher): LessonOut сериализует поле teacher, и без него
    # /api/persons/{id}/schedule делал бы по SELECT на каждую пару (N+1) —
    # у занятого преподавателя это ~150 запросов на один ответ. Как в
    # get_schedule.
    lessons = db.scalars(
        select(Lesson).options(joinedload(Lesson.teacher))
    ).all()
    links = link_lessons(lessons, registry)
    linked_ids = {lid for lid, keys in links.items() if key in keys}
    return [l for l in lessons if l.id in linked_ids]


def person_display(rows: Iterable[PersonRow]) -> list[dict]:
    """Строки справочника → JSON-контракт /api/persons."""
    return [
        {
            "id": row.id,
            "short_name": row.short_name,
            "full_name": row.full_name,
            "sections": row.sections,
            "roles": row.roles,
            "email": row.email,
            "has_schedule": row.has_schedule,
            "lesson_count": row.lesson_count,
            "exam_count": row.exam_count,
        }
        for row in rows
    ]
