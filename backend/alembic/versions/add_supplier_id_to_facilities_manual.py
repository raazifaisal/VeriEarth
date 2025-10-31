"""add_supplier_id_to_facilities_manual

Revision ID: add_supplier_id_manual
Revises: add_org_id_manual
Create Date: 2025-10-29 05:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_supplier_id_manual'
down_revision: Union[str, None] = 'add_org_id_manual'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add supplier_id column to facilities table (nullable)
    op.add_column('facilities', sa.Column('supplier_id', sa.String(), nullable=True))
    
    # Add foreign key constraint
    op.create_foreign_key(
        'facilities_supplier_id_fkey',
        'facilities', 'suppliers',
        ['supplier_id'], ['id']
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('facilities_supplier_id_fkey', 'facilities', type_='foreignkey')
    
    # Remove supplier_id column
    op.drop_column('facilities', 'supplier_id')

