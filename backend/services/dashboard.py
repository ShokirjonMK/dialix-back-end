import logging  # noqa: F401
from uuid import UUID
from decimal import Decimal
from typing import List, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from sqlalchemy import select, func, extract, join, case, String

from backend.database.models import Record, Result, OperatorData


def calculate_percentage(part: int, whole: int) -> int:
    return round((part / whole) * 100) if whole else 0


def get_gender_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> Dict[str, List[Dict]]:
    record_result_join = join(Record, Result, Record.id == Result.record_id)

    query = (
        select(
            Result.customer_gender,
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(Result.customer_gender)
    )
    results = db.execute(query).all()

    total = sum(count for _, count in results)

    data = {
        gender: {"count": count, "percentage": calculate_percentage(count, total)}
        for gender, count in results
    }

    data["total_users"] = total

    return data


def get_leads_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> Dict[str, int]:
    record_result_join = join(Record, Result, Record.id == Result.record_id)

    query = (
        select(
            case(
                (
                    Result.which_platform_customer_found_about_the_course.is_(None),
                    "other",
                ),
                else_=func.lower(Result.which_platform_customer_found_about_the_course),
            ).label("platform"),
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by("platform")
    )

    results = db.execute(query).all()

    data = {lead: count for lead, count in results}

    return data


def get_call_interests_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> Dict[str, int]:
    record_result_join = join(Record, Result, Record.id == Result.record_id)

    query = (
        select(
            case(
                (
                    Result.which_course_customer_interested.is_(None),
                    "other",
                ),
                else_=func.lower(Result.which_course_customer_interested),
            ).label("product"),
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(
            Record.owner_id == owner_id,
            Record.created_at.between(start, end),
            Result.which_course_customer_interested.is_not(None),
        )
        .group_by("product")
    )

    results = db.execute(query).all()

    def clean_product_name(product_name: str):
        return product_name.replace('"', "").replace("}", "").replace("{", "")

    data = {clean_product_name(product): count for product, count in results}

    return data


def get_operator_data(start: datetime, end: datetime, owner_id: UUID, db: Session):
    record_result_operator_join = join(
        Record, Result, Record.id == Result.record_id
    ).join(OperatorData, OperatorData.code.cast(String) == Record.operator_code)

    query = (
        select(
            OperatorData.id,
            OperatorData.code,
            OperatorData.name,
            func.count(Record.id),
            func.avg(Record.duration),
            func.avg(Result.operator_answer_delay),
            func.avg(Result.operator_speech_duration),
        )
        .select_from(record_result_operator_join)
        .where(
            Record.owner_id == owner_id,
            Record.created_at.between(start, end),
        )
        .group_by(OperatorData.id, OperatorData.code, OperatorData.owner_id)
    )

    def seconds_to_str(milliseconds: Decimal) -> str:
        return str(timedelta(milliseconds=int(milliseconds)))

    return [
        {
            "operator_code": operator_code,
            "operator_name": operator_name,
            "recordings_count": recordings_count,
            "avg_call_duration": seconds_to_str(avg_call_duration),
            "avg_answer_delay": seconds_to_str(avg_operator_answer_delay),
            "avg_speech_duration": seconds_to_str(avg_operator_speech_duration),
        }
        for (
            _,
            operator_code,
            operator_name,
            recordings_count,
            avg_call_duration,
            avg_operator_answer_delay,
            avg_operator_speech_duration,
        ) in db.execute(query).all()
    ]


def get_sentiment_analysis_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
):
    def get_sentiment_analysis_by_field(sentiment_field: str):
        record_result_join = join(Record, Result, Record.id == Result.record_id)

        query = (
            select(getattr(Result, sentiment_field), func.count(Record.id))
            .select_from(record_result_join)
            .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
            .group_by(getattr(Result, sentiment_field))
        )
        return {sentiment: count for sentiment, count in db.execute(query).all()}

    def calculate_sentiment_percentage(sentiment_data: dict):
        part = sentiment_data.get("positive", 0) + sentiment_data.get("neutral", 0)
        whole = part + sentiment_data.get("negative", 0)
        return calculate_percentage(part, whole)

    return {
        sentiment_field: calculate_sentiment_percentage(
            get_sentiment_analysis_by_field(sentiment_field)
        )
        for sentiment_field in [
            "sentiment_analysis_of_conversation",
            "sentiment_analysis_of_customer",
            "sentiment_analysis_of_operator",
        ]
    }
