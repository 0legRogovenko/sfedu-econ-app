from datetime import datetime
from datetime import time as time_type

from pydantic import BaseModel, ConfigDict

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
