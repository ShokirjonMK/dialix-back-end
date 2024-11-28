import logging
import typing as t
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import select, func, outerjoin

from backend.utils.parser import parse_order_by
from backend.utils.shortcuts import get_filterable_values_for
from backend.database.models import Record, Result, Checklist
from backend.database.utils import compile_sql_query_and_params

FILTERABLE_COLUMNS: list[str] = [
    "call_type",
    "client_phone_number",
    "operator_code",
    "operator_name",
    "status",
    "duration",
]
ORDERABLE_COLUMNS: list[str] = FILTERABLE_COLUMNS


def get_record_by_title(db_session: Session, owner_id: UUID, title: str) -> Record:
    statement = select(Record).where(
        (Record.owner_id == owner_id) & (Record.title.contains(title))
    )
    return db_session.scalar(statement)


def get_all_record_titles(db_session: Session, owner_id: UUID):
    statement = select(Record.title).where((Record.owner_id == owner_id))
    return db_session.scalars(statement).all()


def get_filterable_values_for_record(
    db_session: Session, owner_id: UUID
) -> dict[str, list[str]]:
    return get_filterable_values_for(Record, FILTERABLE_COLUMNS, db_session, owner_id)


def get_records_sa(  # sa -> SQLAlchemy
    owner_id: UUID,
    operator_code: t.Optional[str] = None,
    operator_name: t.Optional[str] = None,
    call_type: t.Optional[str] = None,
    call_status: t.Optional[str] = None,
    client_phone_number: t.Optional[str] = None,
    transcript_contains: t.Optional[str] = None,
    **order_kwargs,
):
    logging.info(f"{order_kwargs=}")

    statement = select(Record).where(Record.owner_id == owner_id)

    if operator_code:
        statement = statement.where(Record.operator_code == operator_code)

    if operator_name:
        statement = statement.where(Record.operator_name.ilike(operator_name))

    if call_type:
        statement = statement.where(Record.call_type == call_type)

    if call_status:
        statement = statement.where(Record.status == call_status)

    if client_phone_number:
        statement = statement.where(
            Record.client_phone_number.contains(client_phone_number)
        )

    if transcript_contains:
        statement = statement.where(
            Record.payload["result"].op("->>")("text").contains(transcript_contains)
        )

    order_clauses = parse_order_by(Record, order_kwargs)

    logging.info(f"Record => {order_clauses=} {order_kwargs=}")

    if order_clauses:
        statement = statement.order_by(*order_clauses)

    return compile_sql_query_and_params(statement)


def get_records_with_results(
    # record
    owner_id: UUID,
    operator_code: t.Optional[str] = None,
    operator_name: t.Optional[str] = None,
    call_type: t.Optional[str] = None,
    call_status: t.Optional[str] = None,
    client_phone_number: t.Optional[str] = None,
    transcript_contains: t.Optional[str] = None,
    # result
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
    # ordering queries
    order_kwargs_record: t.Optional[dict] = None,
    order_kwargs_result: t.Optional[dict] = None,
):
    # Better version, only for real chads
    # Older version was fetching records first
    # then by iterating over these records, it will query for results
    # which is BAD. This query implements left outer join & json build func.
    statement = (
        select(
            Record,
            func.json_build_object(
                "id",
                Result.id,
                "owner_id",
                Result.owner_id,
                "record_id",
                Result.record_id,
                "checklist_id",
                Result.checklist_id,
                "operator_answer_delay",
                Result.operator_answer_delay,
                "operator_speech_duration",
                Result.operator_speech_duration,
                "customer_speech_duration",
                Result.customer_speech_duration,
                "is_conversation_over",
                Result.is_conversation_over,
                "sentiment_analysis_of_conversation",
                Result.sentiment_analysis_of_conversation,
                "sentiment_analysis_of_operator",
                Result.sentiment_analysis_of_operator,
                "sentiment_analysis_of_customer",
                Result.sentiment_analysis_of_customer,
                "is_customer_satisfied",
                Result.is_customer_satisfied,
                "is_customer_agreed_to_buy",
                Result.is_customer_agreed_to_buy,
                "is_customer_interested_to_product",
                Result.is_customer_interested_to_product,
                "which_course_customer_interested",
                Result.which_course_customer_interested,
                "summary",
                Result.summary,
                "customer_gender",
                Result.customer_gender,
                "checklist_result",
                Result.checklist_result,
                "call_purpose",
                Result.call_purpose,
                "how_old_is_customer",
                Result.how_old_is_customer,
                "reason_for_customer_purchase",
                Result.reason_for_customer_purchase,
                "reason_for_customer_sentiment",
                Result.reason_for_customer_sentiment,
                "reason_for_operator_sentiment",
                Result.reason_for_operator_sentiment,
                "reason_for_conversation_sentiment",
                Result.reason_for_conversation_sentiment,
                "list_of_words_define_customer_sentiment",
                Result.list_of_words_define_customer_sentiment,
                "list_of_words_define_operator_sentiment",
                Result.list_of_words_define_operator_sentiment,
                "which_platform_customer_found_about_the_course",
                Result.which_platform_customer_found_about_the_course,
                "created_at",
                Result.created_at,
                "updated_at",
                Result.updated_at,
                "deleted_at",
                Result.deleted_at,
                "checklist_title",
                Checklist.title,
            ).label("result"),
        )
        .select_from(
            outerjoin(
                Record,
                outerjoin(Result, Checklist, Result.checklist_id == Checklist.id),
                Record.id == Result.record_id,
            )
        )
        .where(Record.owner_id == owner_id)
    )

    # Filters for recording
    if operator_code:
        statement = statement.where(Record.operator_code == operator_code)
    if operator_name:
        statement = statement.where(Record.operator_name.ilike(operator_name))
    if call_type:
        statement = statement.where(Record.call_type == call_type)
    if call_status:
        statement = statement.where(Record.status == call_status)
    if client_phone_number:
        statement = statement.where(
            Record.client_phone_number.contains(client_phone_number)
        )
    if transcript_contains:
        statement = statement.where(
            Record.payload["result"].op("->>")("text").contains(transcript_contains)
        )

    if is_conversation_over is not None:
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
    if is_customer_satisfied is not None:
        statement = statement.where(
            Result.is_customer_satisfied == is_customer_satisfied
        )
    if is_customer_agreed_to_buy is not None:
        statement = statement.where(
            Result.is_customer_agreed_to_buy == is_customer_agreed_to_buy
        )
    if is_customer_interested_to_product is not None:
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

    logging.info(f"Result => {order_kwargs_result=} Record => {order_kwargs_record=}")

    if order_clauses_record := parse_order_by(Record, order_kwargs_record):
        statement = statement.order_by(*order_clauses_record)

    if order_clauses_result := parse_order_by(Result, order_kwargs_result):
        statement = statement.order_by(*order_clauses_result)

    return compile_sql_query_and_params(statement)
