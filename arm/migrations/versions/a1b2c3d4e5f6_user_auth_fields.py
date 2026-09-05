"""user auth fields for multi-user and TOTP

Revision ID: a1b2c3d4e5f6
Revises: 6870a5546912
Create Date: 2026-09-05 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = '6870a5546912'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.add_column(sa.Column('role', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('totp_secret', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('totp_enabled', sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column('backup_codes', sa.Text(), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))

    # Defaults for existing rows
    op.execute("UPDATE user SET role='admin' WHERE role IS NULL")
    op.execute("UPDATE user SET totp_enabled=0 WHERE totp_enabled IS NULL")
    op.execute("UPDATE user SET is_active=1 WHERE is_active IS NULL")


def downgrade():
    with op.batch_alter_table('user') as batch_op:
        batch_op.drop_column('is_active')
        batch_op.drop_column('backup_codes')
        batch_op.drop_column('totp_enabled')
        batch_op.drop_column('totp_secret')
        batch_op.drop_column('role')
