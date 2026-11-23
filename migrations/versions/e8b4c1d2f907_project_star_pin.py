"""project star, pin and hide

Revision ID: e8b4c1d2f907
Revises: d7a3f9c2b815
Create Date: 2026-11-23 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "e8b4c1d2f907"
down_revision = "d7a3f9c2b815"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.add_column(sa.Column("starred", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("pinned", sa.Boolean(), server_default=sa.false(), nullable=False))
        batch_op.add_column(sa.Column("hidden", sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade():
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_column("hidden")
        batch_op.drop_column("pinned")
        batch_op.drop_column("starred")
