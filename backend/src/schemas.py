from datetime import date, datetime
from datetime import time as time_type
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from src.models import EducationLevel, NewsSource, WeekType


class GroupOut(BaseModel):
    """Группа для онбординга.

    У магистров номера группы НЕТ — их идентифицирует программа, и без неё
    клиент видит только number:null и показать их не может. level говорит ему,
    какое из двух полей брать, вместо догадки «number пустой → наверное магистр».
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    course: int
    number: str | None  # у магистров номера группы нет — тогда заполнена program
    program: str | None  # у бакалавров None
    level: EducationLevel
    subgroup_count: int


class TeacherBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str


class LessonOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    weekday: int
    pair_number: int
    starts_at: time_type
    ends_at: time_type
    subject: str
    room: str | None
    week_type: WeekType | None  # null = каждую неделю
    subgroup: int
    teacher: TeacherBrief | None
    # Окно действия пары. null/null = весь семестр (ручные пары, демо-сид).
    # Импортёр заполняет его датами модуля — клиенту достаточно проверить
    # valid_from <= дата <= valid_to, module_id нужен только для группировки.
    module_id: int | None
    valid_from: date | None
    valid_to: date | None


class ModuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None  # имя ключом не является — ключ это диапазон дат
    date_from: date
    date_to: date


class WeekCalendarOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_from: date
    date_to: date
    week_type: WeekType


class ScheduleOut(BaseModel):
    """Пары + контекст для резолвинга «дата → модуль + тип недели».

    Клиент НЕ вычисляет тип недели формулой: существовавшая формула была
    перевёрнута относительно реальности (0 совпадений из 10). Календарь
    недель — данные из файла ЮФУ, сервер отдаёт их как есть.
    """

    lessons: list[LessonOut]
    modules: list[ModuleOut]
    week_calendar: list[WeekCalendarOut]


class ExamEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    subject: str
    teacher: str | None  # 8.1% ячеек без ФИО — дыра источника, не дефект
    consultation_at: datetime | None
    exam_at: datetime | None
    room: str | None  # аудитория экзамена
    kind: str | None  # форма свободным текстом: «устный», «письменный»…


class NewsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    source: NewsSource
    url: str
    image_url: str | None
    is_important: bool
    published_at: datetime


class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section: str
    name: str
    role: str | None
    office: str | None
    email: str | None
    phone: str | None
    office_hours: str | None


class AskRequest(BaseModel):
    # strip_whitespace идёт до проверки длины: "   " — это 422, а не платный
    # вызов модели; " " как device_id — не отдельное ведро квоты
    question: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=1000),
    ]
    device_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
    ]


class AskResponse(BaseModel):
    answer: str
    fallback: bool = False
