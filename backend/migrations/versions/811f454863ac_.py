"""add deliverable tables and level column

Revision ID: 811f454863ac
Revises: c32c2f8d3c75
Create Date: 2026-04-10 20:49:02.388674

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '811f454863ac'
down_revision: Union[str, Sequence[str], None] = 'c32c2f8d3c75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add level column to existing deliverables table
    with op.batch_alter_table('deliverables', schema=None) as batch_op:
        batch_op.add_column(sa.Column(
            'level',
            sa.Enum('PROJECT', 'BUILDING', name='wacodelevel'),
            nullable=False,
            server_default='PROJECT',
        ))

    op.create_table(
        'deliverable_wa_code_triggers',
        sa.Column('deliverable_id', sa.Integer(), nullable=False),
        sa.Column('wa_code_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['deliverable_id'], ['deliverables.id'],
            name=op.f('fk_deliverable_wa_code_triggers_deliverable_id_deliverables'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['wa_code_id'], ['wa_codes.id'],
            name=op.f('fk_deliverable_wa_code_triggers_wa_code_id_wa_codes'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('deliverable_id', 'wa_code_id',
                                name=op.f('pk_deliverable_wa_code_triggers')),
    )

    op.create_table(
        'project_deliverables',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('deliverable_id', sa.Integer(), nullable=False),
        sa.Column(
            'internal_status',
            sa.Enum('INCOMPLETE', 'BLOCKED', 'IN_REVIEW', 'IN_REVISION', 'COMPLETED',
                    name='internaldeliverablestatus'),
            nullable=False,
        ),
        sa.Column(
            'sca_status',
            sa.Enum('PENDING_WA', 'PENDING_RFA', 'OUTSTANDING', 'UNDER_REVIEW',
                    'REJECTED', 'APPROVED', name='scadeliverabledstatus'),
            nullable=False,
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(
            ['deliverable_id'], ['deliverables.id'],
            name=op.f('fk_project_deliverables_deliverable_id_deliverables'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name=op.f('fk_project_deliverables_project_id_projects'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('project_id', 'deliverable_id',
                                name=op.f('pk_project_deliverables')),
    )

    op.create_table(
        'project_building_deliverables',
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('deliverable_id', sa.Integer(), nullable=False),
        sa.Column('school_id', sa.Integer(), nullable=False),
        sa.Column(
            'internal_status',
            sa.Enum('INCOMPLETE', 'BLOCKED', 'IN_REVIEW', 'IN_REVISION', 'COMPLETED',
                    name='internaldeliverablestatus'),
            nullable=False,
        ),
        sa.Column(
            'sca_status',
            sa.Enum('PENDING_WA', 'PENDING_RFA', 'OUTSTANDING', 'UNDER_REVIEW',
                    'REJECTED', 'APPROVED', name='scadeliverabledstatus'),
            nullable=False,
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('added_at', sa.DateTime(),
                  server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.ForeignKeyConstraint(
            ['deliverable_id'], ['deliverables.id'],
            name=op.f('fk_project_building_deliverables_deliverable_id_deliverables'),
            ondelete='RESTRICT',
        ),
        sa.ForeignKeyConstraint(
            ['project_id', 'school_id'],
            ['project_school_links.project_id', 'project_school_links.school_id'],
            name=op.f('fk_project_building_deliverables_project_id_project_school_links'),
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['project_id'], ['projects.id'],
            name=op.f('fk_project_building_deliverables_project_id_projects'),
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('project_id', 'deliverable_id', 'school_id',
                                name=op.f('pk_project_building_deliverables')),
    )


def downgrade() -> None:
    op.drop_table('project_building_deliverables')
    op.drop_table('project_deliverables')
    op.drop_table('deliverable_wa_code_triggers')

    with op.batch_alter_table('deliverables', schema=None) as batch_op:
        batch_op.drop_column('level')
