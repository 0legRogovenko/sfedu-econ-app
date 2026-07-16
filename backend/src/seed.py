"""Сид демо-данных для разработки. Запуск: python -m src.seed"""

from datetime import datetime, time, timedelta

from sqlalchemy import select

from src.database import SessionLocal
from src.models import (
    Contact,
    Group,
    KbArticle,
    Lesson,
    News,
    NewsSource,
    Teacher,
    WeekType,
)

PAIR_TIMES = {
    1: (time(9, 0), time(10, 35)),
    2: (time(10, 50), time(12, 25)),
    3: (time(13, 10), time(14, 45)),
    4: (time(15, 0), time(16, 35)),
}


def seed() -> None:
    session = SessionLocal()
    try:
        if session.scalars(select(Group).limit(1)).first() is not None:
            print("База не пуста — сид пропущен.")
            return

        groups = [
            Group(course=c, number=f"{c}.{n}", subgroup_count=2)
            for c in range(1, 5)
            for n in (1, 2)
        ]
        session.add_all(groups)

        teachers = [
            Teacher(
                full_name="Иванова Елена Петровна",
                department="Кафедра экономической теории",
                email="ivanova@sfedu.ru",
                office="220",
            ),
            Teacher(
                full_name="Петров Андрей Сергеевич",
                department="Кафедра эконометрики",
                email="petrov@sfedu.ru",
                office="305",
            ),
            Teacher(
                full_name="Сидорова Ольга Николаевна",
                department="Кафедра иностранных языков",
                office="118",
            ),
        ]
        session.add_all(teachers)
        session.flush()

        demo = groups[2]  # 2.1
        lessons = [
            Lesson(
                group_id=demo.id, weekday=0, pair_number=1,
                starts_at=PAIR_TIMES[1][0], ends_at=PAIR_TIMES[1][1],
                subject="Макроэкономика", teacher_id=teachers[0].id,
                room="220", week_type=WeekType.BOTH,
            ),
            Lesson(
                group_id=demo.id, weekday=0, pair_number=2,
                starts_at=PAIR_TIMES[2][0], ends_at=PAIR_TIMES[2][1],
                subject="Эконометрика", teacher_id=teachers[1].id,
                room="305", week_type=WeekType.NUMERATOR,
            ),
            Lesson(
                group_id=demo.id, weekday=0, pair_number=2,
                starts_at=PAIR_TIMES[2][0], ends_at=PAIR_TIMES[2][1],
                subject="Статистика", teacher_id=teachers[1].id,
                room="307", week_type=WeekType.DENOMINATOR,
            ),
            Lesson(
                group_id=demo.id, weekday=1, pair_number=1,
                starts_at=PAIR_TIMES[1][0], ends_at=PAIR_TIMES[1][1],
                subject="Иностранный язык", teacher_id=teachers[2].id,
                room="118", week_type=WeekType.BOTH, subgroup=1,
            ),
            Lesson(
                group_id=demo.id, weekday=1, pair_number=1,
                starts_at=PAIR_TIMES[1][0], ends_at=PAIR_TIMES[1][1],
                subject="Иностранный язык", teacher_id=teachers[2].id,
                room="119", week_type=WeekType.BOTH, subgroup=2,
            ),
            Lesson(
                group_id=demo.id, weekday=2, pair_number=3,
                starts_at=PAIR_TIMES[3][0], ends_at=PAIR_TIMES[3][1],
                subject="Микроэкономика", teacher_id=teachers[0].id,
                room="221", week_type=WeekType.BOTH,
            ),
        ]
        session.add_all(lessons)

        now = datetime.now()
        session.add_all(
            [
                News(
                    title="Открыта запись на курсы по выбору",
                    body="Запись открыта до 25 июля в личном кабинете.",
                    source=NewsSource.ECON,
                    url="https://econ.sfedu.ru/news/demo-1",
                    is_important=True,
                    published_at=now - timedelta(hours=2),
                ),
                News(
                    title="Стипендия за июль придёт раньше",
                    body="Выплата запланирована на 20 июля.",
                    source=NewsSource.SFEDU,
                    url="https://sfedu.ru/news/demo-2",
                    published_at=now - timedelta(days=1),
                ),
                News(
                    title="Пересдачи: расписание на август",
                    body="График пересдач опубликован на стенде деканата.",
                    source=NewsSource.ECON,
                    url="https://econ.sfedu.ru/news/demo-3",
                    published_at=now - timedelta(days=2),
                ),
            ]
        )

        session.add_all(
            [
                Contact(
                    section="Деканат", name="Иванова Елена Петровна",
                    role="Декан", office="203", email="dekan.econ@sfedu.ru",
                    office_hours="Пн–Пт 10:00–12:00", sort_order=1,
                ),
                Contact(
                    section="Деканат", name="Сидорова Ольга Николаевна",
                    role="Методист", office="204",
                    office_hours="Пн–Пт 9:00–17:00", sort_order=2,
                ),
                Contact(
                    section="Кафедра экономической теории",
                    name="Петров Андрей Сергеевич",
                    role="Заведующий кафедрой", office="305", sort_order=1,
                ),
            ]
        )

        session.add(
            KbArticle(
                slug="spravka-ob-obuchenii",
                title="Как получить справку об обучении",
                body_md=(
                    "Справку заказывают в деканате (ауд. 203) или по почте "
                    "деканата. Срок изготовления — 3 рабочих дня."
                ),
            )
        )

        session.commit()
        print(
            f"Сид завершён: {len(groups)} групп, {len(teachers)} преподавателей, "
            f"{len(lessons)} пар, 3 новости, 3 контакта, 1 статья базы знаний."
        )
    finally:
        session.close()


if __name__ == "__main__":
    seed()
