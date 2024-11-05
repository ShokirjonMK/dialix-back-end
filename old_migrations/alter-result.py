import psycopg2
import psycopg2.extensions


def up(cursor: psycopg2.extensions.cursor):
    cursor.execute(
        """
        ALTER TABLE "result" ADD "reason_for_customer_purchase" TEXT ;
        ALTER TABLE "result" ADD "which_platform_customer_found_about_the_course" VARCHAR(32) ;
        ALTER TABLE "result" ADD "reason_for_operator_sentiment" TEXT ;
        ALTER TABLE "result" ADD "reason_for_conversation_sentiment" TEXT ;
        ALTER TABLE "result" ADD "list_of_words_define_customer_sentiment" TEXT ;
        ALTER TABLE "result" ADD "how_old_is_customer" VARCHAR(32) ;
        ALTER TABLE "result" ADD "list_of_words_define_operator_sentiment" TEXT ;
        ALTER TABLE "result" ADD "reason_for_customer_sentiment" TEXT ;
        ALTER TABLE "result" ADD "call_purpose" TEXT ;
        """
    )


