from fastapi import FastAPI
from sqladmin import Admin, ModelView
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request

from src import models
from src.config import settings
from src.database import engine


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        if (
            form.get("username") == settings.admin_username
            and form.get("password") == settings.admin_password
        ):
            request.session["admin"] = True
            return True
        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> bool:
        return bool(request.session.get("admin"))


class GroupAdmin(ModelView, model=models.Group):
    name_plural = "Группы"
    column_list = [models.Group.id, models.Group.course, models.Group.number]


class TeacherAdmin(ModelView, model=models.Teacher):
    name_plural = "Преподаватели"
    column_list = [
        models.Teacher.id,
        models.Teacher.full_name,
        models.Teacher.department,
    ]
    column_searchable_list = [models.Teacher.full_name]


class LessonAdmin(ModelView, model=models.Lesson):
    name_plural = "Пары"
    column_list = [
        models.Lesson.id,
        models.Lesson.group,
        models.Lesson.weekday,
        models.Lesson.pair_number,
        models.Lesson.subject,
        models.Lesson.week_type,
    ]


class NewsAdmin(ModelView, model=models.News):
    name_plural = "Новости"
    column_list = [
        models.News.id,
        models.News.title,
        models.News.source,
        models.News.is_important,
        models.News.published_at,
    ]


class ContactAdmin(ModelView, model=models.Contact):
    name_plural = "Контакты"
    column_list = [
        models.Contact.id,
        models.Contact.section,
        models.Contact.name,
        models.Contact.role,
    ]


class KbArticleAdmin(ModelView, model=models.KbArticle):
    name_plural = "База знаний"
    column_list = [models.KbArticle.id, models.KbArticle.slug, models.KbArticle.title]


class AssistantLogAdmin(ModelView, model=models.AssistantLog):
    name_plural = "Логи ассистента"
    column_list = [
        models.AssistantLog.id,
        models.AssistantLog.question,
        models.AssistantLog.created_at,
    ]
    can_create = False
    can_edit = False


def setup_admin(app: FastAPI) -> None:
    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(secret_key=settings.secret_key),
    )
    for view in (
        GroupAdmin,
        TeacherAdmin,
        LessonAdmin,
        NewsAdmin,
        ContactAdmin,
        KbArticleAdmin,
        AssistantLogAdmin,
    ):
        admin.add_view(view)
