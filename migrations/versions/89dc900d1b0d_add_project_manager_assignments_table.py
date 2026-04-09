"""add project_manager_assignments table

Revision ID: 89dc900d1b0d
Revises: bc08a063ad01
Create Date: 2026-04-09 15:11:02.176841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89dc900d1b0d'
down_revision: Union[str, Sequence[str], None] = 'bc08a063ad01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'project_manager_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('assigned_by_id', sa.Integer(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('unassigned_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_by_id'], ['users.id'], name=op.f('fk_project_manager_assignments_assigned_by_id_users'), ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_project_manager_assignments_project_id_projects'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_project_manager_assignments_user_id_users'), ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_project_manager_assignments')),
    )
    with op.batch_alter_table('project_manager_assignments', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_project_manager_assignments_project_id'), ['project_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_project_manager_assignments_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('project_manager_assignments', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_project_manager_assignments_user_id'))
        batch_op.drop_index(batch_op.f('ix_project_manager_assignments_project_id'))

    op.drop_table('project_manager_assignments')
