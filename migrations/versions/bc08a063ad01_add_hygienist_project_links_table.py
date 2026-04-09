"""add project_hygienist_links table

Revision ID: bc08a063ad01
Revises: c9e1f3d72a08
Create Date: 2026-04-09 13:43:34.174479

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bc08a063ad01"
down_revision: Union[str, Sequence[str], None] = "c9e1f3d72a08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_hygienist_links",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("hygienist_id", sa.Integer(), nullable=False),
        sa.Column(
            "assigned_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["hygienist_id"],
            ["hygienists.id"],
            name=op.f("fk_project_hygienist_links_hygienist_id_hygienists"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name=op.f("fk_project_hygienist_links_project_id_projects"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id", name=op.f("pk_project_hygienist_links")
        ),
    )


def downgrade() -> None:
    op.drop_table("project_hygienist_links")
