"""fix install date column

Revision ID: 20251003_fix_install_date
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # First convert existing install_date values to timestamps
    op.execute("""
        UPDATE devices 
        SET install_date = to_timestamp(install_date::bigint)
        WHERE install_date IS NOT NULL 
        AND install_date::text ~ '^[0-9]+$'
    """)

    # Modify the column to always use timestamp
    op.alter_column('devices', 'install_date',
                   type_=sa.TIMESTAMP(timezone=True),
                   postgresql_using='install_date::timestamp with time zone',
                   existing_nullable=True)

def downgrade():
    op.alter_column('devices', 'install_date',
                   type_=sa.TIMESTAMP,
                   postgresql_using='extract(epoch from install_date)::bigint',
                   existing_nullable=True)