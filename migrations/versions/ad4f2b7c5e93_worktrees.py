"""worktrees

Revision ID: ad4f2b7c5e93
Revises: 9c3e1a6f4d82
Create Date: 2026-11-23 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ad4f2b7c5e93"
down_revision = "9c3e1a6f4d82"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "worktree",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("path", sa.String(length=500), nullable=False),
        sa.Column("branch", sa.String(length=120), nullable=False),
        sa.Column("base", sa.String(length=100), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.String(length=80), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["project.id"], name=op.f("fk_worktree_project_id_project")),
        sa.ForeignKeyConstraint(["task_id"], ["task.id"], name=op.f("fk_worktree_task_id_task")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_worktree")),
    )
    with op.batch_alter_table("worktree", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_worktree_project_id"), ["project_id"], unique=False)


def downgrade():
    op.drop_table("worktree")
