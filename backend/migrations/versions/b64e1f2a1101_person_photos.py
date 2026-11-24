"""Add official portrait metadata without modifying people or schedules."""

from alembic import op
import sqlalchemy as sa

revision = "b64e1f2a1101"
down_revision = "f17d2a6c4b91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_photos",
        sa.Column("person_id", sa.String(300), primary_key=True),
        sa.Column("full_name", sa.String(200), nullable=False),
        sa.Column("photo_url", sa.String(1000), nullable=False),
        sa.Column("source_url", sa.String(1000), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("person_photos")
