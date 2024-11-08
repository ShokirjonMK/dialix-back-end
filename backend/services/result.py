import typing as t
from uuid import UUID

from sqlalchemy import select
# from sqlalchemy.orm import Session

from backend.database.models import Result
from backend.database.utils import compile_sql_query_and_params


def get_results_by_record_id_sa(  # sa -> SQLAlchemy
    record_id: UUID,
    owner_id: UUID,
    is_conversation_over: t.Optional[bool] = None,
    sentiment_analysis_of_conversation: t.Optional[str] = None,
    sentiment_analysis_of_operator: t.Optional[str] = None,
    sentiment_analysis_of_customer: t.Optional[str] = None,
    is_customer_satisfied: t.Optional[bool] = None,
    is_customer_agreed_to_buy: t.Optional[bool] = None,
    is_customer_interested_to_product: t.Optional[bool] = None,
    reason_for_customer_purchase: t.Optional[str] = None,
    which_platform_customer_found_about_the_course: t.Optional[str] = None,
    call_purpose: t.Optional[str] = None,
):
    statement = select(Result).where(
        Result.owner_id == owner_id and Result.record_id == record_id
    )

    if is_conversation_over:
        statement = statement.where(Result.is_conversation_over == is_conversation_over)

    if sentiment_analysis_of_conversation:
        statement = statement.where(
            Result.sentiment_analysis_of_conversation.contains(
                sentiment_analysis_of_conversation
            )
        )

    if sentiment_analysis_of_operator:
        statement = statement.where(
            Result.sentiment_analysis_of_operator.contains(
                sentiment_analysis_of_operator
            )
        )
    if sentiment_analysis_of_customer:
        statement = statement.where(
            Result.sentiment_analysis_of_customer.contains(
                sentiment_analysis_of_customer
            )
        )
    if is_customer_satisfied:
        statement = statement.where(
            Result.is_customer_satisfied == is_customer_satisfied
        )
    if is_customer_agreed_to_buy:
        statement = statement.where(
            Result.is_customer_agreed_to_buy == is_customer_agreed_to_buy
        )
    if is_customer_interested_to_product:
        statement = statement.where(
            Result.is_customer_interested_to_product
            == is_customer_interested_to_product
        )
    if reason_for_customer_purchase:
        statement = statement.where(
            Result.reason_for_customer_purchase.contains(reason_for_customer_purchase)
        )
    if which_platform_customer_found_about_the_course:
        statement = statement.where(
            Result.which_platform_customer_found_about_the_course.contains(
                which_platform_customer_found_about_the_course
            )
        )
    if call_purpose:
        statement = statement.where(Result.call_purpose.contains(call_purpose))

    return compile_sql_query_and_params(statement)
