"""merge_heads

Revision ID: 9e9f00c99a13
Revises: 15baf6ca3af5, abc123def456
Create Date: 2025-10-27 05:23:16.051083

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9e9f00c99a13'
down_revision: Union[str, None] = ('15baf6ca3af5', 'abc123def456')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
