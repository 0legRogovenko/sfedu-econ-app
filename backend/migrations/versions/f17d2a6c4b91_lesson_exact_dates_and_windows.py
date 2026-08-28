"""lesson exact dates and valid-window slot key

Revision ID: f17d2a6c4b91
Revises: d96cb86e9d62
Create Date: 2026-08-25 19:30:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f17d2a6c4b91"
down_revision: Union[str, Sequence[str], None] = "d96cb86e9d62"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_OLD_SLOT = [
    "group_id",
    "weekday",
    "pair_number",
    sa.literal_column("coalesce(week_type, '')"),
    "subgroup",
    sa.literal_column("coalesce(module_id, -1)"),
    sa.literal_column("coalesce(document_id, -1)"),
    sa.literal_column("coalesce(date_constraint_raw, '')"),
    "subject",
]

_NEW_SLOT = [
    *_OLD_SLOT[:-1],
    sa.literal_column("coalesce(valid_from, '0001-01-01')"),
    sa.literal_column("coalesce(valid_to, '9999-12-31')"),
    "subject",
]


def upgrade() -> None:
    op.add_column(
        "lessons",
        sa.Column(
            "specific_dates",
            sa.JSON(),
            server_default=sa.text("'[]'"),
            nullable=False,
        ),
    )
    op.drop_index("uq_lessons_slot", table_name="lessons")
    op.create_index("uq_lessons_slot", "lessons", _NEW_SLOT, unique=True)


def downgrade() -> None:
    op.drop_index("uq_lessons_slot", table_name="lessons")
    op.create_index("uq_lessons_slot", "lessons", _OLD_SLOT, unique=True)
    op.drop_column("lessons", "specific_dates")
