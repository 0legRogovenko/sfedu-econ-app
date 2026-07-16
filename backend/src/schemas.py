from datetime import datetime
from datetime import time as time_type
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from src.models import NewsSource, WeekType


class GroupOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course: int
    number: str
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
    week_type: WeekType
    subgroup: int
    teacher: TeacherBrief | None


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
