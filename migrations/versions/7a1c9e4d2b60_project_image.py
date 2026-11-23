"""project image

Revision ID: 7a1c9e4d2b60
Revises: 938f3d9ae289
Create Date: 2026-11-23 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "7a1c9e4d2b60"
down_revision = "938f3d9ae289"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.add_column(sa.Column("image_name", sa.String(length=64), nullable=True))


def downgrade():
    with op.batch_alter_table("project", schema=None) as batch_op:
        batch_op.drop_column("image_name")
