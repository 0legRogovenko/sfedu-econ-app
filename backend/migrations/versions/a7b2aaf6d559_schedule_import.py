"""schedule import

Revision ID: a7b2aaf6d559
Revises: d21ea7659bd9
Create Date: 2026-07-17 13:14:34.786154

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7b2aaf6d559'
down_revision: Union[str, Sequence[str], None] = 'd21ea7659bd9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _enum(*values: str, name: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False)


def upgrade() -> None:
    """Upgrade schema."""
    # --- Новые сущности импорта ------------------------------------------
    op.create_table(
        'schedule_documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('p_doc_id', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(length=200), nullable=False),
        sa.Column('label', sa.String(length=300), nullable=False),
        sa.Column('doc_type', _enum(
            'semester_grid_bachelor', 'semester_grid_master', 'postgrad_dates',
            'exam_session', 'curriculum_page', 'unknown', name='doctype',
        ), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('source_url', sa.String(length=1000), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_schedule_documents')),
        sa.UniqueConstraint('p_doc_id', name=op.f('uq_schedule_documents_p_doc_id')),
    )

    op.create_table(
        'modules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('date_from', sa.Date(), nullable=False),
        sa.Column('date_to', sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'], ['schedule_documents.id'],
            name=op.f('fk_modules_document_id_schedule_documents'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_modules')),
        # Ключ — диапазон дат, а не имя: «2 модуль» встречается дважды
        # с разными датами в одном файле (13470 p5 и p8).
        sa.UniqueConstraint('document_id', 'date_from', 'date_to', name=op.f('uq_modules_document_id')),
    )
    op.create_index(op.f('ix_modules_document_id'), 'modules', ['document_id'], unique=False)

    op.create_table(
        'week_calendars',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('date_from', sa.Date(), nullable=False),
        sa.Column('date_to', sa.Date(), nullable=False),
        sa.Column('week_type', _enum('upper', 'lower', name='weektype'), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'], ['schedule_documents.id'],
            name=op.f('fk_week_calendars_document_id_schedule_documents'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_week_calendars')),
        sa.UniqueConstraint('document_id', 'date_from', 'date_to', name=op.f('uq_week_calendars_document_id')),
    )
    op.create_index(op.f('ix_week_calendars_document_id'), 'week_calendars', ['document_id'], unique=False)

    op.create_table(
        'unparsed_cells',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('page', sa.Integer(), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('reason', sa.String(length=200), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['document_id'], ['schedule_documents.id'],
            name=op.f('fk_unparsed_cells_document_id_schedule_documents'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_unparsed_cells')),
    )
    op.create_index(op.f('ix_unparsed_cells_document_id'), 'unparsed_cells', ['document_id'], unique=False)

    op.create_table(
        'exam_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('group_id', sa.Integer(), nullable=False),
        sa.Column('subject', sa.String(length=300), nullable=False),
        sa.Column('teacher', sa.String(length=200), nullable=True),
        sa.Column('consultation_at', sa.DateTime(), nullable=True),
        sa.Column('exam_at', sa.DateTime(), nullable=True),
        sa.Column('room', sa.String(length=50), nullable=True),
        sa.Column('kind', sa.String(length=50), nullable=True),
        sa.Column('cell_raw', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ['group_id'], ['groups.id'],
            name=op.f('fk_exam_events_group_id_groups'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_exam_events')),
    )
    op.create_index(op.f('ix_exam_events_group_id'), 'exam_events', ['group_id'], unique=False)

    # --- Group: у магистров номера НЕТ, есть программа --------------------
    op.alter_column('groups', 'number', existing_type=sa.String(length=20), nullable=True)
    op.add_column('groups', sa.Column(
        'level', _enum('bachelor', 'master', name='educationlevel'),
        nullable=False, server_default='bachelor',
    ))
    # server_default нужен только чтобы залить существующие строки; в модели
    # его нет — снимаем, иначе autogenerate будет вечно видеть дрейф.
    op.alter_column('groups', 'level', server_default=None)
    op.add_column('groups', sa.Column('program', sa.String(length=300), nullable=True))

    op.drop_constraint('uq_groups_course', 'groups', type_='unique')
    op.create_index(
        'uq_groups_identity', 'groups',
        ['course', sa.text("coalesce(number, '')"), sa.text("coalesce(program, '')")],
        unique=True,
    )

    # --- Lesson: модули, вид занятия, сырьё, nullable week_type -----------
    op.add_column('lessons', sa.Column('module_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        op.f('fk_lessons_module_id_modules'), 'lessons', 'modules',
        ['module_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index(op.f('ix_lessons_module_id'), 'lessons', ['module_id'], unique=False)
    op.add_column('lessons', sa.Column(
        'lesson_kind', _enum('lecture', 'seminar', name='lessonkind'), nullable=True,
    ))
    op.add_column('lessons', sa.Column('date_constraint_raw', sa.String(length=100), nullable=True))
    op.add_column('lessons', sa.Column('cell_raw', sa.Text(), nullable=True))

    # Старое ограничение включает week_type — снимаем до правки данных.
    op.drop_constraint('uq_lessons_group_id', 'lessons', type_='unique')
    op.alter_column('lessons', 'week_type', existing_type=sa.VARCHAR(length=11), nullable=True)

    # numerator|denominator|both → upper|lower|NULL.
    # 'both' означал «каждую неделю» — теперь это NULL, основной случай.
    op.execute("""
        UPDATE lessons SET week_type = CASE week_type
            WHEN 'numerator' THEN 'upper'
            WHEN 'denominator' THEN 'lower'
            ELSE NULL
        END
    """)

    # Тип сужается VARCHAR(11) → VARCHAR(5) только ПОСЛЕ конвертации данных:
    # 'denominator' в пять символов не влезает.
    op.alter_column(
        'lessons', 'week_type',
        existing_type=sa.VARCHAR(length=11),
        type_=_enum('upper', 'lower', name='weektype'),
        existing_nullable=True,
    )

    op.create_index(
        'uq_lessons_slot', 'lessons',
        [
            'group_id', 'weekday', 'pair_number',
            sa.text("coalesce(week_type, '')"),
            'subgroup',
            sa.text('coalesce(module_id, -1)'),
        ],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_lessons_slot', table_name='lessons')

    # Расширяем тип ДО записи данных: 'denominator' — 11 символов.
    op.alter_column(
        'lessons', 'week_type',
        existing_type=_enum('upper', 'lower', name='weektype'),
        type_=sa.VARCHAR(length=11),
        existing_nullable=True,
    )
    op.execute("""
        UPDATE lessons SET week_type = CASE week_type
            WHEN 'upper' THEN 'numerator'
            WHEN 'lower' THEN 'denominator'
            ELSE 'both'
        END
    """)
    op.execute("UPDATE lessons SET week_type = 'both' WHERE week_type IS NULL")
    op.alter_column('lessons', 'week_type', existing_type=sa.VARCHAR(length=11), nullable=False)
    op.create_unique_constraint(
        'uq_lessons_group_id', 'lessons',
        ['group_id', 'weekday', 'pair_number', 'week_type', 'subgroup'],
    )

    op.drop_column('lessons', 'cell_raw')
    op.drop_column('lessons', 'date_constraint_raw')
    op.drop_column('lessons', 'lesson_kind')
    op.drop_index(op.f('ix_lessons_module_id'), table_name='lessons')
    op.drop_constraint(op.f('fk_lessons_module_id_modules'), 'lessons', type_='foreignkey')
    op.drop_column('lessons', 'module_id')

    op.drop_index('uq_groups_identity', table_name='groups')
    op.drop_column('groups', 'program')
    op.drop_column('groups', 'level')
    # Магистры вниз не едут: без number строка не удовлетворяет старой схеме.
    op.execute("DELETE FROM groups WHERE number IS NULL")
    op.alter_column('groups', 'number', existing_type=sa.VARCHAR(length=20), nullable=False)
    op.create_unique_constraint('uq_groups_course', 'groups', ['course', 'number'])

    op.drop_index(op.f('ix_exam_events_group_id'), table_name='exam_events')
    op.drop_table('exam_events')
    op.drop_index(op.f('ix_unparsed_cells_document_id'), table_name='unparsed_cells')
    op.drop_table('unparsed_cells')
    op.drop_index(op.f('ix_week_calendars_document_id'), table_name='week_calendars')
    op.drop_table('week_calendars')
    op.drop_index(op.f('ix_modules_document_id'), table_name='modules')
    op.drop_table('modules')
    op.drop_table('schedule_documents')
