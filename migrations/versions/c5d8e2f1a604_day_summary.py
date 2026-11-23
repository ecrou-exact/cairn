"""day summary

Revision ID: c5d8e2f1a604
Revises: ad4f2b7c5e93
Create Date: 2026-11-23 13:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c5d8e2f1a604"
down_revision = "ad4f2b7c5e93"
branch_labels = None
depends_on = None


def _base():
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def upgrade():
    op.create_table(
        "work_target",
        sa.Column("label", sa.String(length=80), nullable=False),
        sa.Column("repos", sa.JSON(), nullable=False),
        sa.Column("keywords", sa.JSON(), nullable=False),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("guidance", sa.Text(), nullable=False),
        sa.Column("about", sa.String(length=500), nullable=False),
        sa.Column("kimai_project", sa.Integer(), nullable=False),
        sa.Column("project_label", sa.String(length=160), nullable=False),
        sa.Column("kimai_activity", sa.Integer(), nullable=False),
        sa.Column("activity_label", sa.String(length=160), nullable=False),
        sa.Column("tags", sa.JSON(), nullable=False),
        *_base(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_target")),
    )
    op.create_table(
        "work_day",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("facts", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary_md", sa.Text(), nullable=False),
        sa.Column("summary_edited", sa.Boolean(), nullable=False),
        *_base(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_day")),
        sa.UniqueConstraint("day", name=op.f("uq_work_day_day")),
    )
    op.create_table(
        "day_entry",
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("begin", sa.String(length=5), nullable=False),
        sa.Column("minutes", sa.Integer(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("kimai_id", sa.Integer(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        *_base(),
        sa.ForeignKeyConstraint(
            ["target_id"], ["work_target.id"], name=op.f("fk_day_entry_target_id_work_target")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_day_entry")),
    )
    with op.batch_alter_table("day_entry", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_day_entry_day"), ["day"], unique=False)


def downgrade():
    op.drop_table("day_entry")
    op.drop_table("work_day")
    op.drop_table("work_target")
