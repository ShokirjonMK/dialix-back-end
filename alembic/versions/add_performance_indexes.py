"""Add performance indexes

Revision ID: add_performance_indexes
Revises: add_company_management_and_activity_logging
Create Date: 2024-01-01 12:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_performance_indexes"
down_revision = "add_company_management_and_activity_logging"
branch_labels = None
depends_on = None


def upgrade():
    # Activity logs indexes
    op.create_index(
        "idx_activity_log_user_id", "activity_log", ["user_id"], unique=False
    )

    op.create_index(
        "idx_activity_log_created_at", "activity_log", ["created_at"], unique=False
    )

    op.create_index(
        "idx_activity_log_resource",
        "activity_log",
        ["resource_type", "resource_id"],
        unique=False,
    )

    # User management indexes
    op.create_index("idx_account_email", "account", ["email"], unique=False)

    op.create_index("idx_account_company_id", "account", ["company_id"], unique=False)

    op.create_index("idx_account_is_active", "account", ["is_active"], unique=False)

    # Records indexes
    op.create_index(
        "idx_record_owner_status", "record", ["owner_id", "status"], unique=False
    )

    op.create_index(
        "idx_record_client_phone", "record", ["client_phone_number"], unique=False
    )

    op.create_index("idx_record_created_at", "record", ["created_at"], unique=False)

    # Results indexes
    op.create_index(
        "idx_result_owner_created", "result", ["owner_id", "created_at"], unique=False
    )

    op.create_index("idx_result_record_id", "result", ["record_id"], unique=False)

    # Transaction indexes
    op.create_index(
        "idx_transaction_owner_type", "transaction", ["owner_id", "type"], unique=False
    )

    op.create_index(
        "idx_transaction_created_at", "transaction", ["created_at"], unique=False
    )

    # Company indexes
    op.create_index("idx_company_is_active", "company", ["is_active"], unique=False)


def downgrade():
    # Remove all indexes
    op.drop_index("idx_activity_log_user_id", table_name="activity_log")
    op.drop_index("idx_activity_log_created_at", table_name="activity_log")
    op.drop_index("idx_activity_log_resource", table_name="activity_log")

    op.drop_index("idx_account_email", table_name="account")
    op.drop_index("idx_account_company_id", table_name="account")
    op.drop_index("idx_account_is_active", table_name="account")

    op.drop_index("idx_record_owner_status", table_name="record")
    op.drop_index("idx_record_client_phone", table_name="record")
    op.drop_index("idx_record_created_at", table_name="record")

    op.drop_index("idx_result_owner_created", table_name="result")
    op.drop_index("idx_result_record_id", table_name="result")

    op.drop_index("idx_transaction_owner_type", table_name="transaction")
    op.drop_index("idx_transaction_created_at", table_name="transaction")

    op.drop_index("idx_company_is_active", table_name="company")
