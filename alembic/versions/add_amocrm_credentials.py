"""add amocrm credentials

Revision ID: add_amocrm_credentials
Revises: 093bc905877a
Create Date: 2025-10-28

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_amocrm_credentials"
down_revision: Union[str, None] = "093bc905877a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "amocrm_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("owner_id", sa.UUID(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=False),
        sa.Column("access_token", sa.String(), nullable=False),
        sa.Column("refresh_token", sa.String(), nullable=True),
        sa.Column("client_id", sa.String(), nullable=True),
        sa.Column("client_secret", sa.String(), nullable=True),
        sa.Column("redirect_uri", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["owner_id"], ["account.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner_id"),
        sa.UniqueConstraint("base_url"),
    )


def downgrade() -> None:
    op.drop_table("amocrm_credentials")
