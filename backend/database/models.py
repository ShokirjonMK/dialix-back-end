from uuid import uuid4

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    JSON,
    Boolean,
    BigInteger,
    TIMESTAMP,
    TEXT,
    Integer,
    text,
    relationship,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID


from backend.database import Base


class Account(Base):
    __tablename__ = "account"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    email = Column(String, nullable=False, unique=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    company_name = Column(String, nullable=False)  # LEGACY - use company_id instead
    company_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=True
    )  # NEW
    is_active = Column(Boolean, server_default="true")  # NEW
    is_blocked = Column(Boolean, server_default="false")  # NEW
    last_activity = Column(TIMESTAMP, nullable=True)  # NEW
    preferred_language = Column(String, default="uz")  # NEW
    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)

    # Relationships
    company_rel = relationship("Company", back_populates="users")


class Record(Base):
    __tablename__ = "record"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    title = Column(String, nullable=False)
    duration = Column(BigInteger)
    payload = Column(JSON)
    operator_code = Column(String, nullable=True)
    operator_name = Column(String, nullable=True)
    call_type = Column(String, nullable=True)
    source = Column(String)
    status = Column(String)
    storage_id = Column(String)
    client_phone_number = Column(String, nullable=True)
    bitrix_result = Column(JSON)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    deleted_at = Column(TIMESTAMP)


class Transaction(Base):
    __tablename__ = "transaction"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    amount = Column(BigInteger, nullable=False)
    type = Column(String, nullable=False)
    record_id = Column(PostgresUUID(as_uuid=True), ForeignKey("record.id"))
    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class Checklist(Base):
    __tablename__ = "checklist"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    title = Column(String, nullable=False)
    payload = Column(JSON)
    active = Column(Boolean, server_default="false", nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    deleted_at = Column(TIMESTAMP)


class Result(Base):
    __tablename__ = "result"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    record_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("record.id"), nullable=False
    )
    checklist_id = Column(PostgresUUID(as_uuid=True), ForeignKey("checklist.id"))
    operator_answer_delay = Column(BigInteger)
    operator_speech_duration = Column(BigInteger)
    customer_speech_duration = Column(BigInteger)
    is_conversation_over = Column(Boolean)
    sentiment_analysis_of_conversation = Column(String)
    sentiment_analysis_of_operator = Column(String)
    sentiment_analysis_of_customer = Column(String)
    is_customer_satisfied = Column(Boolean)
    is_customer_agreed_to_buy = Column(Boolean)
    is_customer_interested_to_product = Column(Boolean)
    which_course_customer_interested = Column(String)
    summary = Column(String)
    customer_gender = Column(String)
    checklist_result = Column(JSON)

    call_purpose = Column(TEXT)
    how_old_is_customer = Column(String)
    reason_for_customer_purchase = Column(TEXT)
    reason_for_customer_sentiment = Column(TEXT)
    reason_for_operator_sentiment = Column(TEXT)
    reason_for_conversation_sentiment = Column(TEXT)
    list_of_words_define_customer_sentiment = Column(TEXT)
    list_of_words_define_operator_sentiment = Column(TEXT)
    which_platform_customer_found_about_the_course = Column(String)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    deleted_at = Column(TIMESTAMP)


class BlackListToken(Base):
    __tablename__ = "blacklist_token"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    value = Column(TEXT)


class OperatorData(Base):
    __tablename__ = "operator_data"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    code = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=text("now()"))
    updated_at = Column(
        TIMESTAMP, nullable=False, server_default=text("now()"), onupdate=text("now()")
    )
    deleted_at = Column(TIMESTAMP, nullable=True)


class PbxCredentials(Base):
    __tablename__ = "pbx_credentials"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    owner_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("account.id"),
        nullable=False,
        unique=True,
    )
    api_key = Column(String, nullable=False)
    domain = Column(String, unique=True, nullable=False)

    key = Column(String, nullable=True, default=None)
    key_id = Column(String, nullable=True, default=None)


class BitrixCredentials(Base):
    __tablename__ = "bitrix_credentials"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    owner_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("account.id"),
        nullable=False,
        unique=True,
    )
    webhook_url = Column(String, unique=True, nullable=False)


class AmoCRMCredentials(Base):
    __tablename__ = "amocrm_credentials"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)

    owner_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("account.id"),
        nullable=False,
        unique=True,
    )

    # Base URL like: https://<subdomain>.amocrm.ru
    base_url = Column(String, unique=True, nullable=False)

    # OAuth2 tokens (if provided manually for now)
    access_token = Column(String, nullable=False)
    refresh_token = Column(String, nullable=True)

    # Optional OAuth2 client details for future token refresh automation
    client_id = Column(String, nullable=True)
    client_secret = Column(String, nullable=True)
    redirect_uri = Column(String, nullable=True)


class PbxCall(Base):
    """PBX qo'ng'iroqlari"""

    __tablename__ = "pbx_calls"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    call_id = Column(PostgresUUID(as_uuid=True), nullable=False, unique=True)
    caller_id_name = Column(String, nullable=True)
    caller_id_number = Column(String, nullable=True)
    destination_number = Column(String, nullable=True)
    start_stamp = Column(BigInteger, nullable=True)
    end_stamp = Column(BigInteger, nullable=True)
    duration = Column(Integer, nullable=True)
    user_talk_time = Column(Integer, nullable=True)
    call_type = Column(String, nullable=True)
    bitrix_result = Column(JSON, nullable=True)
    was_processed_from_bitrix = Column(Boolean, server_default="false", nullable=False)


class Company(Base):
    """Company Management uchun model"""

    __tablename__ = "company"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    name = Column(String, nullable=False, unique=True)
    description = Column(TEXT, nullable=True)
    is_active = Column(Boolean, server_default="true", nullable=False)
    parent_company_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=True
    )
    hierarchy_level = Column(Integer, server_default="0", nullable=False)
    settings = Column(JSON, nullable=True)  # Company-specific settings
    balance = Column(BigInteger, server_default="0", nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)

    # Relationships
    users = relationship("Account", back_populates="company_rel")
    administrators = relationship("CompanyAdministrator", back_populates="company")


class CompanyAdministrator(Base):
    """Kompaniya adminlari"""

    __tablename__ = "company_administrator"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=False
    )
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    permissions = Column(JSON, nullable=True)  # {"can_manage_users": true, ...}

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)

    # Relationships
    company = relationship("Company", back_populates="administrators")


class UserCompanyHistory(Base):
    """User o'tkazilgan kompaniyalar tarixi"""

    __tablename__ = "user_company_history"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    company_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("company.id"), nullable=False
    )
    action = Column(String, nullable=False)  # "transferred", "joined", "left"
    balance_at_time = Column(BigInteger, nullable=True)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class ActivityLog(Base):
    """CRUD operations uchun audit log"""

    __tablename__ = "activity_log"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    action = Column(String, nullable=False)  # "CREATE", "UPDATE", "DELETE", "VIEW"
    resource_type = Column(
        String, nullable=False
    )  # "record", "checklist", "operator", "account"
    resource_id = Column(PostgresUUID(as_uuid=True), nullable=False)
    details = Column(
        JSON, nullable=True
    )  # {"field": "value", "old_value": "...", "new_value": "..."}
    ip_address = Column(String, nullable=True)
    user_agent = Column(TEXT, nullable=True)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class AIChatSession(Base):
    """AI Chat interface uchun session"""

    __tablename__ = "ai_chat_session"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    record_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("record.id"), nullable=False
    )
    session_data = Column(
        JSON, nullable=True
    )  # {"questions_asked": 5, "context": {...}}
    is_active = Column(Boolean, server_default="true", nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class AIChatMessage(Base):
    """AI Chat xabarlar"""

    __tablename__ = "ai_chat_message"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    session_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("ai_chat_session.id"), nullable=False
    )
    role = Column(String, nullable=False)  # "user", "assistant"
    content = Column(TEXT, nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class UserSettings(Base):
    """User sozlamalari"""

    __tablename__ = "user_settings"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(
        PostgresUUID(as_uuid=True),
        ForeignKey("account.id"),
        nullable=False,
        unique=True,
    )

    # Notification settings
    email_notifications = Column(Boolean, server_default="true", nullable=False)
    sms_notifications = Column(Boolean, server_default="false", nullable=False)
    push_notifications = Column(Boolean, server_default="true", nullable=False)

    # Language & localization
    language = Column(String, server_default="uz", nullable=False)
    timezone = Column(String, server_default="Asia/Tashkent", nullable=False)

    # Data retention
    auto_delete_records_after_days = Column(
        Integer, server_default="90", nullable=False
    )

    # STT Model preferences
    preferred_stt_model = Column(String, server_default="mohirai", nullable=False)

    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
