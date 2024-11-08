from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "result" ADD "reason_for_operator_sentiment" TEXT NOT NULL;
        ALTER TABLE "result" ADD "reason_for_customer_purchase" TEXT NOT NULL;
        ALTER TABLE "result" ADD "call_purpose" TEXT NOT NULL;
        ALTER TABLE "result" ADD "reason_for_customer_sentiment" TEXT NOT NULL;
        ALTER TABLE "result" ADD "list_of_words_define_customer_sentiment" TEXT NOT NULL;
        ALTER TABLE "result" ADD "which_platform_customer_found_about_the_course" VARCHAR(32) NOT NULL;
        ALTER TABLE "result" ADD "how_old_is_customer" VARCHAR(32) NOT NULL;
        ALTER TABLE "result" ADD "list_of_words_define_operator_sentiment" TEXT NOT NULL;
        ALTER TABLE "result" ADD "reason_for_conversation_sentiment" TEXT NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE "result" DROP COLUMN "reason_for_operator_sentiment";
        ALTER TABLE "result" DROP COLUMN "reason_for_customer_purchase";
        ALTER TABLE "result" DROP COLUMN "call_purpose";
        ALTER TABLE "result" DROP COLUMN "reason_for_customer_sentiment";
        ALTER TABLE "result" DROP COLUMN "list_of_words_define_customer_sentiment";
        ALTER TABLE "result" DROP COLUMN "which_platform_customer_found_about_the_course";
        ALTER TABLE "result" DROP COLUMN "how_old_is_customer";
        ALTER TABLE "result" DROP COLUMN "list_of_words_define_operator_sentiment";
        ALTER TABLE "result" DROP COLUMN "reason_for_conversation_sentiment";"""
