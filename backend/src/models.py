import enum
from datetime import date, datetime, time

from sqlalchemy import (
    Enum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database import Base


def _enum(enum_cls: type[enum.Enum]) -> Enum:
    """Enum-колонка, которая пишется в БД ЗНАЧЕНИЯМИ, а не именами членов.

    Без values_callable SQLAlchemy кладёт в VARCHAR имя ('UPPER') вместо
    значения ('upper'). Проект на это уже наступал: ORM подменяет обратно
    и молчит, а расходятся API-контракт, миграция и сырой SQL.
    """
    return Enum(
        enum_cls,
        native_enum=False,
        values_callable=lambda e: [m.value for m in e],
    )


class WeekType(enum.Enum):
    # Термины ЮФУ. «Числителя/знаменателя» в корпусе нет ни разу.
    UPPER = "upper"  # верхняя неделя
    LOWER = "lower"  # нижняя неделя


class EducationLevel(enum.Enum):
    BACHELOR = "bachelor"
    MASTER = "master"


class LessonKind(enum.Enum):
    LECTURE = "lecture"  # (л)
    SEMINAR = "seminar"  # (с)


class DocType(enum.Enum):
    SEMESTER_GRID_BACHELOR = "semester_grid_bachelor"
    SEMESTER_GRID_MASTER = "semester_grid_master"
    POSTGRAD_DATES = "postgrad_dates"
    EXAM_SESSION = "exam_session"
    CURRICULUM_PAGE = "curriculum_page"
    UNKNOWN = "unknown"


class NewsSource(enum.Enum):
    SFEDU = "sfedu"
    ECON = "econ"


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    course: Mapped[int]
    # У магистров номера группы НЕТ — их идентифицирует программа
    number: Mapped[str | None] = mapped_column(String(20))
    level: Mapped[EducationLevel] = mapped_column(
        _enum(EducationLevel), default=EducationLevel.BACHELOR
    )
    program: Mapped[str | None] = mapped_column(String(300))
    subgroup_count: Mapped[int] = mapped_column(default=1)

    __table_args__ = (
        # Не UniqueConstraint(course, number): number у магистров NULL, а NULL
        # в SQL не конфликтует сам с собой — уникальность стала бы фикцией.
        Index(
            "uq_groups_identity",
            "course",
            text("coalesce(number, '')"),
            text("coalesce(program, '')"),
            unique=True,
        ),
    )


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    department: Mapped[str | None] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(200))
    office: Mapped[str | None] = mapped_column(String(50))
    office_hours: Mapped[str | None] = mapped_column(String(200))


class ScheduleDocument(Base):
    """Файл расписания с сайта ЮГУ. p_doc_id — стабильный ключ слота:
    файл подменяется на месте, id не меняется. Last-Modified/ETag у файлов
    нет — sha256 единственный сигнал обновления."""

    __tablename__ = "schedule_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    p_doc_id: Mapped[int] = mapped_column(unique=True)
    section: Mapped[str] = mapped_column(String(200))
    label: Mapped[str] = mapped_column(String(300))
    doc_type: Mapped[DocType] = mapped_column(_enum(DocType))
    sha256: Mapped[str] = mapped_column(String(64))
    fetched_at: Mapped[datetime] = mapped_column(server_default=func.now())
    source_url: Mapped[str] = mapped_column(String(1000))


class WeekCalendar(Base):
    """Таблица 1 семестрового файла: диапазон дат → верхняя/нижняя.
    Импортируется как данные; формула «чётная ISO = верхняя» — только ассерт."""

    __tablename__ = "week_calendars"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    date_from: Mapped[date]
    date_to: Mapped[date]
    week_type: Mapped[WeekType] = mapped_column(_enum(WeekType))

    document: Mapped["ScheduleDocument"] = relationship()

    __table_args__ = (
        UniqueConstraint("document_id", "date_from", "date_to"),
    )


class Module(Base):
    """Период семестра со своей таблицей пар. Основное измерение расписания;
    чередование недель — редкое исключение."""

    __tablename__ = "modules"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    # Имя ключом НЕ является: «2 модуль» встречается дважды с разными датами
    # в одном файле (13470 p5 и p8). Ключ — диапазон дат.
    name: Mapped[str | None] = mapped_column(String(100))
    date_from: Mapped[date]
    date_to: Mapped[date]

    document: Mapped["ScheduleDocument"] = relationship()

    __table_args__ = (
        UniqueConstraint("document_id", "date_from", "date_to"),
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE")
    )
    # Откуда пара приехала. Без этой ссылки переразбор изменившегося файла
    # не может заменить его пары: module_id nullable, и пары без модуля
    # (основной случай) не привязаны к документу ничем. NULL — ручная пара
    # или демо-сид.
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    module_id: Mapped[int | None] = mapped_column(
        ForeignKey("modules.id", ondelete="CASCADE"), index=True
    )
    weekday: Mapped[int]  # 0 = понедельник … 5 = суббота
    pair_number: Mapped[int]
    starts_at: Mapped[time]
    ends_at: Mapped[time]
    subject: Mapped[str] = mapped_column(String(200))
    lesson_kind: Mapped[LessonKind | None] = mapped_column(_enum(LessonKind))
    teacher_id: Mapped[int | None] = mapped_column(
        ForeignKey("teachers.id", ondelete="SET NULL"), index=True
    )
    room: Mapped[str | None] = mapped_column(String(50))
    # NULL = каждую неделю. Это ОСНОВНОЙ случай: маркер типа недели
    # встречается 6 раз на весь корпус ЮФУ.
    week_type: Mapped[WeekType | None] = mapped_column(_enum(WeekType))
    subgroup: Mapped[int] = mapped_column(default=0)  # 0 = вся группа
    date_constraint_raw: Mapped[str | None] = mapped_column(String(100))
    # Хранится ВСЕГДА, даже для успешно разобранных: стоит байты,
    # окупается при первой жалобе «у нас не та аудитория».
    cell_raw: Mapped[str | None] = mapped_column(Text)
    # Координата породившей ячейки: "таблица:строка:колонка" в пределах
    # документа, тот же ключ, что у Ledger. Без неё у строки БД нет связи
    # с ячейкой, и prove() вынужден сверять МНОЖЕСТВА текстов — а множества
    # не отличают «ячейка породила свои пары» от «где-то есть строка с таким
    # текстом»: ячейки-близнецы делят одно доказательство, внутриячеечная
    # потеря и мусорная строка проходят незамеченными. NULL — ручная пара.
    cell_key: Mapped[str | None] = mapped_column(String(50))
    valid_from: Mapped[date | None]
    valid_to: Mapped[date | None]
    # A sparse list such as '08.11, 15.11' cannot be represented faithfully
    # by one continuous window. ISO strings keep SQLite and PostgreSQL aligned.
    specific_dates: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default=text("'[]'"),
    )

    group: Mapped["Group"] = relationship()
    module: Mapped["Module | None"] = relationship()
    teacher: Mapped["Teacher | None"] = relationship()

    __table_args__ = (
        # Не UniqueConstraint: week_type и module_id nullable, а NULL в SQL
        # не конфликтует сам с собой — дубли основного случая (каждую неделю,
        # без модуля) прошли бы молча. coalesce закрывает обе дыры.
        #
        # document_id в ключе обязателен: у одной группы осенний и весенний
        # семестры — РАЗНЫЕ файлы с одинаковыми (день, пара). Без него импорт
        # весны падал на уникальности осени, а «починка» дедупом молча стёрла
        # бы половину года.
        Index(
            "uq_lessons_slot",
            "group_id",
            "weekday",
            "pair_number",
            text("coalesce(week_type, '')"),
            "subgroup",
            text("coalesce(module_id, -1)"),
            text("coalesce(document_id, -1)"),
            # Две пары в одной ячейке различаются ТОЛЬКО датами ('До 17.12' и
            # '24.12' в 13469): без этого поля вторая молча не сохранилась бы.
            text("coalesce(date_constraint_raw, '')"),
            text("coalesce(valid_from, '0001-01-01')"),
            text("coalesce(valid_to, '9999-12-31')"),
            # …а параллельные занятия — только предметом ('Иностранный язык (с)
            # Онлайн' + 'Русский язык для иностранных студентов (с)' в одной
            # ячейке, 13472 p3). Слот у них общий, и это не дубль.
            "subject",
            unique=True,
        ),
    )


class UnparsedCell(Base):
    """Непустая ячейка, не легшая в Lesson/ExamEvent. Ничего не теряем молча —
    всё сюда с исходным текстом и причиной, дальше в очередь админа."""

    __tablename__ = "unparsed_cells"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    page: Mapped[int | None]
    raw_text: Mapped[str] = mapped_column(Text)
    reason: Mapped[str] = mapped_column(String(200))
    # Координата породившей ячейки (см. Lesson.cell_key). NULL — фрагмент без
    # ячейки: аномалия календаря недель или неразобранный кусок сессии.
    cell_key: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped["ScheduleDocument"] = relationship()


class ExamEvent(Base):
    __tablename__ = "exam_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    subject: Mapped[str] = mapped_column(String(300))
    teacher: Mapped[str | None] = mapped_column(String(200))
    consultation_at: Mapped[datetime | None]
    exam_at: Mapped[datetime | None]
    room: Mapped[str | None] = mapped_column(String(50))
    # Форма: 'устный', 'письменный', 'онлайн устный'… Не enum — корпус
    # пишет её свободным текстом, а угадывать значения не на чем.
    kind: Mapped[str | None] = mapped_column(String(50))
    cell_raw: Mapped[str | None] = mapped_column(Text)

    group: Mapped["Group"] = relationship()


class ImportDiff(Base):
    """Что изменилось в документе при переразборе: «было/стало» для админа.

    ЮФУ подменяет файл на месте (p_doc_id тот же, sha256 новый). Молча
    перезаписать пары нельзя: студент увидит другую аудиторию и не узнает,
    что расписание меняли. Поэтому каждое изменение кладётся сюда.
    """

    __tablename__ = "import_diffs"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_documents.id", ondelete="CASCADE"), index=True
    )
    sha256_before: Mapped[str] = mapped_column(String(64))
    sha256_after: Mapped[str] = mapped_column(String(64))
    added: Mapped[int] = mapped_column(default=0)
    removed: Mapped[int] = mapped_column(default=0)
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    document: Mapped["ScheduleDocument"] = relationship()


class News(Base):
    __tablename__ = "news"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[NewsSource] = mapped_column(_enum(NewsSource))
    url: Mapped[str] = mapped_column(String(1000), unique=True)
    image_url: Mapped[str | None] = mapped_column(String(1000))
    is_important: Mapped[bool] = mapped_column(default=False)
    published_at: Mapped[datetime] = mapped_column(index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ContactSource(str, enum.Enum):
    MANUAL = "manual"          # заведено админом
    ECON_SITE = "econ_site"    # автозабор с econ-sfedu.ru


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

    # Кто завёл запись. Автозабор с econ-sfedu.ru владеет ТОЛЬКО своими
    # строками и при повторном запуске заменяет именно их: иначе он стирал бы
    # то, что админ вписал руками (кабинеты, часы приёма, почты — их на сайте
    # факультета нет).
    source: Mapped[str] = mapped_column(String(20), default=ContactSource.MANUAL)


class DirectoryOverride(Base):
    """Ручная правка единого справочника поверх автозабора.

    Живёт на СЛОЕ ЧТЕНИЯ: build_directory применяет её после сборки списка.
    Поэтому автозабор её не видит и не может затереть — он сколько угодно раз
    переливает contacts, а правка остаётся. Сюда попадает то, чего на сайте
    факультета нет или что там неверно: почты заведующих (их личные страницы
    отдают 404) и скрытие людей, которых в справочнике быть не должно.

    Матчинг по `match_name` — короткому «Фамилия И.О.»: из него считается тот
    же ключ (фамилия + оба инициала), что и у человека в справочнике.
    """

    __tablename__ = "directory_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_name: Mapped[str] = mapped_column(String(200))  # «Погорелова Т.Г.»
    email: Mapped[str | None] = mapped_column(String(200))
    hidden: Mapped[bool] = mapped_column(default=False)


class SubjectRename(Base):
    """Кураторское переименование предмета на СЛОЕ ЧТЕНИЯ.

    В исходных PDF встречаются кривые названия («Институциональна я экономика»
    — перенос без дефиса, «Data Sciience» — опечатка). Импортёр хранит текст
    дословно (верность источнику + инвариант доказуемости), а красивое имя
    подставляется при отдаче API. Автозабор правку не видит и не затирает.

    Матчинг — по точному тексту предмета, как он лежит в lessons.subject /
    exam_events.subject.
    """

    __tablename__ = "subject_renames"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_subject: Mapped[str] = mapped_column(String(500), unique=True)
    display_subject: Mapped[str] = mapped_column(String(500))


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
