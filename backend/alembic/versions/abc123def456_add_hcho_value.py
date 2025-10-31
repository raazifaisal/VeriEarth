"""add_hcho_value_to_environmental_data

Revision ID: abc123def456
Revises: 86872397397f
Create Date: 2025-01-28 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'abc123def456'
down_revision: Union[str, None] = '86872397397f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add hcho_value column to facility_environmental_data table
    op.add_column('facility_environmental_data', sa.Column('hcho_value', sa.Float(), nullable=True))


def downgrade() -> None:
    # Remove hcho_value column
    op.drop_column('facility_environmental_data', 'hcho_value')

