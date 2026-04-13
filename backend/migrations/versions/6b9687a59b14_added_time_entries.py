"""added time entries

Revision ID: 6b9687a59b14
Revises: 811f454863ac
Create Date: 2026-04-12 15:46:51.369376

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6b9687a59b14'
down_revision: Union[str, Sequence[str], None] = '811f454863ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'time_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('start_datetime', sa.DateTime(), nullable=False),
        sa.Column('end_datetime', sa.DateTime(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('employee_role_id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column('notes', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(
            ['employee_id'], ['employees.id'],
            name=op.f('fk_time_entries_employee_id_employees'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['employee_role_id'], ['employee_roles.id'],
            name=op.f('fk_time_entries_employee_role_id_employee_roles'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name=op.f('fk_time_entries_project_id_projects'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['project_id', 'school_id'],
            ['project_school_links.project_id', 'project_school_links.school_id'],
            name=op.f('fk_time_entries_project_id_project_school_links'),
            ondelete='RESTRICT',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_time_entries')),
    )
    op.create_index(op.f('ix_time_entries_employee_id'), 'time_entries',
                    ['employee_id'], unique=False)
    op.create_index(op.f('ix_time_entries_employee_role_id'), 'time_entries',
                    ['employee_role_id'], unique=False)
    op.create_index(op.f('ix_time_entries_project_id'), 'time_entries',
                    ['project_id'], unique=False)
    op.create_index(op.f('ix_time_entries_school_id'), 'time_entries',
                    ['school_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_time_entries_school_id'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_project_id'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_employee_role_id'), table_name='time_entries')
    op.drop_index(op.f('ix_time_entries_employee_id'), table_name='time_entries')
    op.drop_table('time_entries')
