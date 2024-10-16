from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "account" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "email" VARCHAR(255) NOT NULL UNIQUE,
    "username" VARCHAR(255) NOT NULL UNIQUE,
    "password" VARCHAR(255) NOT NULL,
    "role" VARCHAR(255) NOT NULL,
    "company_name" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS "checklist" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "payload" JSONB,
    "active" BOOL NOT NULL  DEFAULT False,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "owner_id" UUID NOT NULL REFERENCES "account" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "operatordata" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "code" INT NOT NULL,
    "name" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "owner_id" UUID NOT NULL REFERENCES "account" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "record" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "title" VARCHAR(255) NOT NULL,
    "duration" BIGINT,
    "payload" JSONB,
    "operator_code" VARCHAR(255),
    "operator_name" VARCHAR(255),
    "call_type" VARCHAR(255),
    "source" VARCHAR(255),
    "status" VARCHAR(255),
    "storage_id" VARCHAR(255),
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "owner_id" UUID NOT NULL REFERENCES "account" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "result" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "operator_answer_delay" BIGINT,
    "operator_speech_duration" BIGINT,
    "customer_speech_duration" BIGINT,
    "is_conversation_over" BOOL,
    "sentiment_analysis_of_conversation" VARCHAR(255),
    "sentiment_analysis_of_operator" VARCHAR(255),
    "sentiment_analysis_of_customer" VARCHAR(255),
    "is_customer_satisfied" BOOL,
    "is_customer_agreed_to_buy" BOOL,
    "is_customer_interested_to_product" BOOL,
    "which_course_customer_interested" VARCHAR(255),
    "summary" VARCHAR(255),
    "customer_gender" VARCHAR(255),
    "checklist_result" JSONB,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "deleted_at" TIMESTAMPTZ,
    "checklist_id" UUID REFERENCES "checklist" ("id") ON DELETE CASCADE,
    "owner_id" UUID NOT NULL REFERENCES "account" ("id") ON DELETE CASCADE,
    "record_id" UUID NOT NULL REFERENCES "record" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "transaction" (
    "id" UUID NOT NULL  PRIMARY KEY,
    "amount" BIGINT NOT NULL,
    "type" VARCHAR(255) NOT NULL,
    "created_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "updated_at" TIMESTAMPTZ NOT NULL  DEFAULT CURRENT_TIMESTAMP,
    "owner_id" UUID NOT NULL REFERENCES "account" ("id") ON DELETE CASCADE,
    "record_id" UUID REFERENCES "record" ("id") ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" SERIAL NOT NULL PRIMARY KEY,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSONB NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
