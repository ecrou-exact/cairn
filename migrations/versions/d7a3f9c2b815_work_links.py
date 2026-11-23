"""work links

Revision ID: d7a3f9c2b815
Revises: c5d8e2f1a604
Create Date: 2026-11-23 14:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "d7a3f9c2b815"
down_revision = "c5d8e2f1a604"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "work_link",
        sa.Column("target_type", sa.String(length=12), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=10), nullable=False),
        sa.Column("ref", sa.String(length=500), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_work_link")),
    )
    with op.batch_alter_table("work_link", schema=None) as batch_op:
        batch_op.create_index("ix_work_link_target", ["target_type", "target_id"], unique=False)


def downgrade():
    op.drop_table("work_link")
