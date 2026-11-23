"""claude requests

Revision ID: 8b2d0f5e3c71
Revises: 7a1c9e4d2b60
Create Date: 2026-11-23 10:30:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "8b2d0f5e3c71"
down_revision = "7a1c9e4d2b60"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "claude_request",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("work", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=10), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=True),
        sa.Column("error", sa.String(length=300), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["project.id"], name=op.f("fk_claude_request_project_id_project")
        ),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], name=op.f("fk_claude_request_task_id_task")),
        sa.ForeignKeyConstraint(
            ["session_id"], ["claude_session.id"], name=op.f("fk_claude_request_session_id_claude_session")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_claude_request")),
    )
    with op.batch_alter_table("claude_request", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_claude_request_status"), ["status"], unique=False)


def downgrade():
    op.drop_table("claude_request")
