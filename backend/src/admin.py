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


class ScheduleDocumentAdmin(ModelView, model=models.ScheduleDocument):
    name_plural = "Файлы расписания"
    column_list = [
        models.ScheduleDocument.p_doc_id,
        models.ScheduleDocument.section,
        models.ScheduleDocument.label,
        models.ScheduleDocument.doc_type,
        models.ScheduleDocument.fetched_at,
    ]
    column_searchable_list = [models.ScheduleDocument.label]
    can_create = False  # документы заводит импортёр, руками их не выдумывают


class UnparsedCellAdmin(ModelView, model=models.UnparsedCell):
    """Очередь вычитки. Здесь лежит всё, что парсер честно не осилил — и это
    единственная причина, по которой оно не потерялось молча."""

    name = "Очередь вычитки"
    name_plural = "Очередь вычитки"
    column_list = [
        models.UnparsedCell.id,
        models.UnparsedCell.document,
        models.UnparsedCell.page,
        models.UnparsedCell.reason,
        models.UnparsedCell.raw_text,
        models.UnparsedCell.created_at,
    ]
    column_searchable_list = [models.UnparsedCell.reason, models.UnparsedCell.raw_text]
    column_sortable_list = [models.UnparsedCell.created_at, models.UnparsedCell.page]
    can_create = False
    can_edit = False


class ExamEventAdmin(ModelView, model=models.ExamEvent):
    name_plural = "Экзамены"
    column_list = [
        models.ExamEvent.id,
        models.ExamEvent.group,
        models.ExamEvent.subject,
        models.ExamEvent.consultation_at,
        models.ExamEvent.exam_at,
        models.ExamEvent.room,
        models.ExamEvent.kind,
    ]
    column_searchable_list = [models.ExamEvent.subject]


class ImportDiffAdmin(ModelView, model=models.ImportDiff):
    name_plural = "Изменения расписания"
    column_list = [
        models.ImportDiff.id,
        models.ImportDiff.document,
        models.ImportDiff.added,
        models.ImportDiff.removed,
        models.ImportDiff.created_at,
    ]
    can_create = False
    can_edit = False


class ModuleAdmin(ModelView, model=models.Module):
    name_plural = "Модули"
    column_list = [
        models.Module.id,
        models.Module.document,
        models.Module.name,
        models.Module.date_from,
        models.Module.date_to,
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


class DirectoryOverrideAdmin(ModelView, model=models.DirectoryOverride):
    name_plural = "Правки справочника"
    column_list = [
        models.DirectoryOverride.id,
        models.DirectoryOverride.match_name,
        models.DirectoryOverride.email,
        models.DirectoryOverride.hidden,
    ]


class SubjectRenameAdmin(ModelView, model=models.SubjectRename):
    """Переименования кривых предметов из PDF: точный текст → красивое имя."""

    name = "Переименование предмета"
    name_plural = "Переименования предметов"
    column_list = [
        models.SubjectRename.id,
        models.SubjectRename.match_subject,
        models.SubjectRename.display_subject,
    ]
    column_searchable_list = [models.SubjectRename.match_subject]


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
    can_delete = False


def setup_admin(app: FastAPI) -> None:
    if not settings.admin_enabled:
        return

    admin = Admin(
        app,
        engine,
        authentication_backend=AdminAuth(secret_key=settings.secret_key),
    )
    for view in (
        GroupAdmin,
        TeacherAdmin,
        LessonAdmin,
        UnparsedCellAdmin,
        ScheduleDocumentAdmin,
        ExamEventAdmin,
        ImportDiffAdmin,
        ModuleAdmin,
        NewsAdmin,
        ContactAdmin,
        DirectoryOverrideAdmin,
        SubjectRenameAdmin,
        KbArticleAdmin,
        AssistantLogAdmin,
    ):
        admin.add_view(view)
