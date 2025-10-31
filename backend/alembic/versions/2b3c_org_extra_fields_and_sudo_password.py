"""add org extra fields and sudo password

Revision ID: 2b3c_add_org_fields
Revises: 86872397397f
Create Date: 2025-10-31
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2b3c_add_org_fields'
down_revision = '86872397397f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('organizations', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('organizations', sa.Column('address', sa.Text(), nullable=True))
    op.add_column('organizations', sa.Column('details', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    op.add_column('organizations', sa.Column('sudo_password_hash', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('organizations', 'sudo_password_hash')
    op.drop_column('organizations', 'details')
    op.drop_column('organizations', 'address')
    op.drop_column('organizations', 'description')


