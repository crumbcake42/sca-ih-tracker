"""Add hygienists, wa_codes, deliverables, employee_roles tables

Revision ID: c9e1f3d72a08
Revises: a2c67c7b3e72
Create Date: 2026-04-07 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9e1f3d72a08'
down_revision: Union[str, Sequence[str], None] = 'a2c67c7b3e72'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'hygienists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=14), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_hygienists')),
        sa.UniqueConstraint('email', name=op.f('uq_hygienists_email')),
        sa.UniqueConstraint('phone', name=op.f('uq_hygienists_phone')),
    )

    op.create_table(
        'wa_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.Column('level', sa.Enum('project', 'building', name='wacodelevel'), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_wa_codes')),
        sa.UniqueConstraint('code', name=op.f('uq_wa_codes_code')),
        sa.UniqueConstraint('description', name=op.f('uq_wa_codes_description')),
    )
    op.create_index(op.f('ix_wa_codes_code'), 'wa_codes', ['code'], unique=True)

    op.create_table(
        'deliverables',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_deliverables')),
        sa.UniqueConstraint('name', name=op.f('uq_deliverables_name')),
    )
    op.create_index(op.f('ix_deliverables_name'), 'deliverables', ['name'], unique=True)

    op.create_table(
        'employee_roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column(
            'role_type',
            sa.Enum(
                'Air Monitor', 'Air Technician', 'Project Monitor', 'Lead Risk Assessor',
                name='employeeroletype',
            ),
            nullable=False,
        ),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('hourly_rate', sa.Numeric(precision=10, scale=2), nullable=False),
        sa.ForeignKeyConstraint(
            ['employee_id'], ['employees.id'],
            name=op.f('fk_employee_roles_employee_id_employees'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_employee_roles')),
    )
    op.create_index(op.f('ix_employee_roles_employee_id'), 'employee_roles', ['employee_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_employee_roles_employee_id'), table_name='employee_roles')
    op.drop_table('employee_roles')

    op.drop_index(op.f('ix_deliverables_name'), table_name='deliverables')
    op.drop_table('deliverables')

    op.drop_index(op.f('ix_wa_codes_code'), table_name='wa_codes')
    op.drop_table('wa_codes')

    op.drop_table('hygienists')
