"""add organization_id to routes and shipments

Revision ID: add_org_id_manual
Revises: 9e9f00c99a13
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_org_id_manual'
down_revision = '9e9f00c99a13'
branch_labels = None
depends_on = None


def upgrade():
    # Add organization_id to routes table (nullable first)
    op.add_column('routes', sa.Column('organization_id', sa.String(), nullable=True))
    
    # Update existing routes with organization_id from their origin facility
    op.execute("""
        UPDATE routes 
        SET organization_id = f.organization_id 
        FROM facilities f 
        WHERE routes.origin_facility_id = f.id
    """)
    
    # Now make it NOT NULL
    op.alter_column('routes', 'organization_id', nullable=False)
    op.create_foreign_key('fk_routes_organization_id', 'routes', 'organizations', ['organization_id'], ['id'])
    
    # Add organization_id to shipments table (nullable first)
    op.add_column('shipments', sa.Column('organization_id', sa.String(), nullable=True))
    
    # Update existing shipments with organization_id from their route
    op.execute("""
        UPDATE shipments 
        SET organization_id = r.organization_id 
        FROM routes r 
        WHERE shipments.route_id = r.id
    """)
    
    # Now make it NOT NULL
    op.alter_column('shipments', 'organization_id', nullable=False)
    op.create_foreign_key('fk_shipments_organization_id', 'shipments', 'organizations', ['organization_id'], ['id'])


def downgrade():
    # Remove organization_id from shipments table
    op.drop_constraint('fk_shipments_organization_id', 'shipments', type_='foreignkey')
    op.drop_column('shipments', 'organization_id')
    
    # Remove organization_id from routes table
    op.drop_constraint('fk_routes_organization_id', 'routes', type_='foreignkey')
    op.drop_column('routes', 'organization_id')
