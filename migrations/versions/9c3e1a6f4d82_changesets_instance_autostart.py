"""changesets, instance autostart

Revision ID: 9c3e1a6f4d82
Revises: 8b2d0f5e3c71
Create Date: 2026-11-23 11:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9c3e1a6f4d82"
down_revision = "8b2d0f5e3c71"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "changeset",
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("reason_md", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], name=op.f("fk_changeset_project_id_project")),
        sa.ForeignKeyConstraint(
            ["session_id"], ["claude_session.id"], name=op.f("fk_changeset_session_id_claude_session")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_changeset")),
    )
    with op.batch_alter_table("changeset", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_changeset_status"), ["status"], unique=False)
    with op.batch_alter_table("project_instance", schema=None) as batch_op:
        batch_op.add_column(sa.Column("autostart", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    with op.batch_alter_table("project_instance", schema=None) as batch_op:
        batch_op.drop_column("autostart")
    op.drop_table("changeset")
