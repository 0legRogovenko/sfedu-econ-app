import enum
from datetime import date, datetime, time

from sqlalchemy import Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


class WeekType(enum.Enum):
    NUMERATOR = "numerator"      # числитель
    DENOMINATOR = "denominator"  # знаменатель
    BOTH = "both"


class NewsSource(enum.Enum):
    SFEDU = "sfedu"
    ECON = "econ"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    course: Mapped[int]
    number: Mapped[str] = mapped_column(String(20))
    subgroup_count: Mapped[int] = mapped_column(default=1)

    __table_args__ = (UniqueConstraint("course", "number"),)


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    office: Mapped[str | None] = mapped_column(String(50))
    office_hours: Mapped[str | None] = mapped_column(String(200))


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE")
    )
    weekday: Mapped[int]  # 0 = понедельник … 5 = суббота
    pair_number: Mapped[int]
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    subject: Mapped[str] = mapped_column(String(200))
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    room: Mapped[str | None] = mapped_column(String(50))
    week_type: Mapped[WeekType] = mapped_column(
        Enum(WeekType, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=WeekType.BOTH,
    )
    subgroup: Mapped[int] = mapped_column(default=0)  # 0 = вся группа
    valid_from: Mapped[date | None]
    valid_to: Mapped[date | None]

    group: Mapped["Group"] = relationship()
    teacher: Mapped["Teacher | None"] = relationship()

    __table_args__ = (
        UniqueConstraint(
            "group_id", "weekday", "pair_number", "week_type", "subgroup"
        ),
    )


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[NewsSource] = mapped_column(
        Enum(NewsSource, native_enum=False, values_callable=lambda e: [m.value for m in e])
    )
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    is_important: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    section: Mapped[str] = mapped_column(String(200))  # «Деканат», кафедра…
    name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str | None] = mapped_column(String(200))
    office: Mapped[str | None] = mapped_column(String(50))
    email: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(50))
    office_hours: Mapped[str | None] = mapped_column(String(200))
    sort_order: Mapped[int] = mapped_column(default=0)


class KbArticle(Base):
    __tablename__ = "kb_articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    body_md: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )


class AssistantLog(Base):
    __tablename__ = "assistant_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    device_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
