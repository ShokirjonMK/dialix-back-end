"""Add company management and activity logging

Revision ID: add_company_management
Revises: 756a5e6ef826
Create Date: 2024-12-20

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "add_company_management"
down_revision: Union[str, None] = "756a5e6ef826"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new columns to account table
    op.add_column("account", sa.Column("company_id", sa.UUID(), nullable=True))
    op.add_column(
        "account",
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
    )
    op.add_column(
        "account",
        sa.Column("is_blocked", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column("account", sa.Column("last_activity", sa.TIMESTAMP(), nullable=True))
    op.add_column(
        "account",
        sa.Column(
            "preferred_language", sa.String(), server_default="uz", nullable=False
        ),
    )

    # Create company table
    op.create_table(
        "company",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.TEXT(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("parent_company_id", sa.UUID(), nullable=True),
        sa.Column("hierarchy_level", sa.Integer(), server_default="0", nullable=False),
        sa.Column("settings", sa.JSON(), nullable=True),
        sa.Column("balance", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    # Create company_administrator table
    op.create_table(
        "company_administrator",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_company_history table
    op.create_table(
        "user_company_history",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("company_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("balance_at_time", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create activity_log table
    op.create_table(
        "activity_log",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=False),
        sa.Column("resource_id", sa.UUID(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.TEXT(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ai_chat_session table
    op.create_table(
        "ai_chat_session",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("record_id", sa.UUID(), nullable=False),
        sa.Column("session_data", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create ai_chat_message table
    op.create_table(
        "ai_chat_message",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content", sa.TEXT(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create user_settings table
    op.create_table(
        "user_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "email_notifications", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column(
            "sms_notifications", sa.Boolean(), server_default="false", nullable=False
        ),
        sa.Column(
            "push_notifications", sa.Boolean(), server_default="true", nullable=False
        ),
        sa.Column("language", sa.String(), server_default="uz", nullable=False),
        sa.Column(
            "timezone", sa.String(), server_default="Asia/Tashkent", nullable=False
        ),
        sa.Column(
            "auto_delete_records_after_days",
            sa.Integer(),
            server_default="90",
            nullable=False,
        ),
        sa.Column(
            "preferred_stt_model", sa.String(), server_default="mohirai", nullable=False
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )

    # Add foreign keys
    op.create_foreign_key(
        "fk_account_company", "account", "company", ["company_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_company_administrator_company",
        "company_administrator",
        "company",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_company_administrator_user",
        "company_administrator",
        "account",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_user_company_history_user",
        "user_company_history",
        "account",
        ["user_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_user_company_history_company",
        "user_company_history",
        "company",
        ["company_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_activity_log_user", "activity_log", "account", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_ai_chat_session_user", "ai_chat_session", "account", ["user_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_ai_chat_session_record", "ai_chat_session", "record", ["record_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_ai_chat_message_session",
        "ai_chat_message",
        "ai_chat_session",
        ["session_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_user_settings_user", "user_settings", "account", ["user_id"], ["id"]
    )

    # Create indexes for performance
    op.create_index("idx_account_company_id", "account", ["company_id"])
    op.create_index("idx_account_is_active", "account", ["is_active"])
    op.create_index("idx_activity_log_user_id", "activity_log", ["user_id"])
    op.create_index("idx_activity_log_created_at", "activity_log", ["created_at"])
    op.create_index(
        "idx_activity_log_resource", "activity_log", ["resource_type", "resource_id"]
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_activity_log_resource", "activity_log")
    op.drop_index("idx_activity_log_created_at", "activity_log")
    op.drop_index("idx_activity_log_user_id", "activity_log")
    op.drop_index("idx_account_is_active", "account")
    op.drop_index("idx_account_company_id", "account")

    # Drop foreign keys
    op.drop_constraint("fk_user_settings_user", "user_settings")
    op.drop_constraint("fk_ai_chat_message_session", "ai_chat_message")
    op.drop_constraint("fk_ai_chat_session_record", "ai_chat_session")
    op.drop_constraint("fk_ai_chat_session_user", "ai_chat_session")
    op.drop_constraint("fk_activity_log_user", "activity_log")
    op.drop_constraint("fk_user_company_history_company", "user_company_history")
    op.drop_constraint("fk_user_company_history_user", "user_company_history")
    op.drop_constraint("fk_company_administrator_user", "company_administrator")
    op.drop_constraint("fk_company_administrator_company", "company_administrator")
    op.drop_constraint("fk_account_company", "account")

    # Drop tables
    op.drop_table("user_settings")
    op.drop_table("ai_chat_message")
    op.drop_table("ai_chat_session")
    op.drop_table("activity_log")
    op.drop_table("user_company_history")
    op.drop_table("company_administrator")
    op.drop_table("company")

    # Remove columns from account
    op.drop_column("account", "preferred_language")
    op.drop_column("account", "last_activity")
    op.drop_column("account", "is_blocked")
    op.drop_column("account", "is_active")
    op.drop_column("account", "company_id")
