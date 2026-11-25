"""time entries: changed by hand, own place and tags, what was sent

Revision ID: f2a6b7c8d913
Revises: e8b4c1d2f907
Create Date: 2026-11-25 15:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

revision = "f2a6b7c8d913"
down_revision = "e8b4c1d2f907"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("day_entry", schema=None) as batch_op:
        # entries made before may have been changed by hand: none is refreshed on its own
        batch_op.add_column(sa.Column("edited", sa.Boolean(), server_default=sa.true(), nullable=False))
        batch_op.add_column(sa.Column("place", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("tags", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("sent_as", sa.JSON(), nullable=True))


def downgrade():
    with op.batch_alter_table("day_entry", schema=None) as batch_op:
        batch_op.drop_column("sent_as")
        batch_op.drop_column("tags")
        batch_op.drop_column("place")
        batch_op.drop_column("edited")
