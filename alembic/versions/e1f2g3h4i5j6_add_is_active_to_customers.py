"""add_is_active_to_customers

Revision ID: e1f2g3h4i5j6
Revises: c05cef608ff0
Create Date: 2026-02-18 15:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1f2g3h4i5j6'
down_revision: Union[str, Sequence[str], None] = 'c05cef608ff0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('customers', sa.Column('is_active', sa.Boolean(), nullable=True, server_default=sa.text('1')))


def downgrade() -> None:
    op.drop_column('customers', 'is_active')
