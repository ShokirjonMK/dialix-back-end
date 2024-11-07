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
    company_name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)
    updated_at = Column(TIMESTAMP, server_default=text("now()"), nullable=False)


class Record(Base):
    __tablename__ = "record"

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
    owner_id = Column(
        PostgresUUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    title = Column(String, nullable=False)
    duration = Column(BigInteger)
    payload = Column(JSON)
    operator_code = Column(String)
    operator_name = Column(String)
    call_type = Column(String)
    source = Column(String)
    status = Column(String)
    client_phone_number = Column(String)
    storage_id = Column(String)
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

    id = Column(PostgresUUID(as_uuid=True), primary_key=True)
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
