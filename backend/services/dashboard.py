import logging  # noqa: F401
import typing as t
from uuid import UUID
from math import floor
from statistics import median
from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import select, join, case, String, func

from backend.database.models import Record, Result, OperatorData


def calculate_percentage(part: int, whole: int) -> int:
    return round((part / whole) * 100) if whole else 0


def calculate_score(checklist_result: dict) -> float:
    total_fields = 0
    true_values = 0

    for segment in checklist_result.values():
        total_fields += len(segment)
        true_values += sum(1 for val in segment.values() if val)

    calculation_result = (true_values / total_fields) * 100 if total_fields > 0 else 0

    logging.info(f"{calculation_result=} for {checklist_result=}")

    return calculation_result


def get_gender_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, list[dict]]:
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


def get_call_purpose_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, int]:
    record_result_join = join(Record, Result, Record.id == Result.record_id)

    query = (
        select(
            case(
                (
                    Result.call_purpose.is_(None),
                    "other",
                ),
                else_=func.lower(Result.call_purpose),
            ).label("purpose"),
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by("purpose")
    )

    results = db.execute(query).all()

    data = {lead: count for lead, count in results}

    return data


def get_leads_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, int]:
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
) -> dict[str, int]:
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


def get_sentiment_analysis_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, int]:
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


def get_leads_data_daily(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, list[dict]]:
    record_result_join = join(Record, Result, Record.id == Result.record_id)

    query = (
        select(
            func.date(Record.created_at).label("date"),
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
        .group_by("date", "platform")
    )

    results = db.execute(query).all()

    all_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    formatted_dates = [date.strftime("%Y-%m-%d") for date in all_dates]

    daily_leads = {}

    for date, platform, count in results:
        formatted_date = date.strftime("%Y-%m-%d")
        if platform not in daily_leads:
            daily_leads[platform] = {d: 0 for d in formatted_dates}

        daily_leads[platform][formatted_date] = count

    result = {
        platform: [
            {"date": date, "count": daily_leads[platform].get(date, 0)}
            for date in formatted_dates
        ]
        for platform in daily_leads
    }

    return result


def get_operator_data(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> list[dict]:
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

    operator_scores = get_operator_performance(start, end, owner_id, db)

    return [
        {
            "operator_code": operator_code,
            "operator_name": operator_name,
            "recordings_count": recordings_count,
            "avg_call_duration": seconds_to_str(avg_call_duration),
            "avg_answer_delay": seconds_to_str(avg_operator_answer_delay),
            "avg_speech_duration": seconds_to_str(avg_operator_speech_duration),
            "avg_score": operator_scores.get(operator_code, {}).get("avg_score", 0),
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


def get_operator_performance(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, dict[str, t.Any]]:
    record_result_operator_join = join(
        Record, Result, Record.id == Result.record_id
    ).join(OperatorData, OperatorData.code.cast(String) == Record.operator_code)

    query = (
        select(
            OperatorData.code,
            OperatorData.name,
            Result.checklist_result,
        )
        .select_from(record_result_operator_join)
        .where(
            Record.owner_id == owner_id,
            Record.created_at.between(start, end),
        )
    )

    results = db.execute(query).all()

    operator_scores = {}

    for code, name, checklist_result in results:
        score = calculate_score(checklist_result)
        if code in operator_scores:
            operator_scores[code]["scores"].append(score)
        else:
            operator_scores[code] = {"name": name, "scores": [score]}

    return {
        code: {
            "name": data["name"],
            "avg_score": floor(sum(data["scores"]) / len(data["scores"])),
        }
        for code, data in operator_scores.items()
    }


def get_operator_performance_daily(
    start: datetime, end: datetime, owner_id: UUID, db: Session
) -> dict[str, list[dict]]:
    record_result_operator_join = join(
        Record, Result, Record.id == Result.record_id
    ).join(OperatorData, OperatorData.code.cast(String) == Record.operator_code)

    query = (
        select(
            OperatorData.code,
            OperatorData.name,
            func.date(Record.created_at).label("date"),
            Result.checklist_result,
        )
        .select_from(record_result_operator_join)
        .where(
            Record.owner_id == owner_id,
            Record.created_at.between(start, end),
        )
    )

    results = db.execute(query).all()

    all_dates = [start + timedelta(days=i) for i in range((end - start).days + 1)]
    formatted_dates = [date.strftime("%Y-%m-%d") for date in all_dates]

    daily_scores = {}

    for code, name, date, checklist_result in results:
        score = calculate_score(checklist_result)

        if code not in daily_scores:
            daily_scores[code] = {
                "name": name,
                "daily_scores": {d: None for d in formatted_dates},
            }

        if (daily_scores[code]["daily_scores"][date.strftime("%Y-%m-%d")]) is None:
            daily_scores[code]["daily_scores"][date.strftime("%Y-%m-%d")] = [score]
        else:
            daily_scores[code]["daily_scores"][date.strftime("%Y-%m-%d")].append(score)

    result = {}

    def calculate_avg_score(value: t.Any) -> t.Any:
        if value is None:
            return None

        return floor(median(value))

    for code, data in daily_scores.items():
        result[code] = {
            "name": data["name"],
            "daily_scores": [
                {
                    "date": date,
                    "avg_score": calculate_avg_score(data["daily_scores"][date]),
                }
                for date in formatted_dates
            ],
        }

    return result


def calculate_daily_satisfaction(data):
    current_date = datetime.now().date()
    last_month_start = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_of_last_month = current_date.replace(day=1) - timedelta(days=1)
    current_month_start = current_date.replace(day=1)
    end_of_current_month = (
        current_month_start.replace(day=28) + timedelta(days=4)
    ).replace(day=1) - timedelta(days=1)

    # Initialize dictionaries to hold satisfaction counts for each day
    last_month_satisfaction = {}
    current_month_satisfaction = {}

    # Generate string formatted dates for keys
    last_month_days = [
        (last_month_start + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((end_of_last_month - last_month_start).days + 1)
    ]
    current_month_days = [
        (current_month_start + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range((end_of_current_month - current_month_start).days + 1)
    ]

    for day in last_month_days:
        last_month_satisfaction[day] = 0
    for day in current_month_days:
        current_month_satisfaction[day] = 0

    # Distribute satisfaction counts into the respective dictionaries
    for entry in data:
        date_of_result = datetime.strptime(
            entry["result_created_at"], "%Y-%m-%dT%H:%M:%S.%f"
        ).date()
        date_str = date_of_result.strftime("%Y-%m-%d")
        if entry["is_customer_satisfied"]:
            if last_month_start <= date_of_result <= end_of_last_month:
                if date_str in last_month_satisfaction:
                    last_month_satisfaction[date_str] += 1
                else:
                    logging.warning(
                        f"Date {date_str} is out of expected range for last month."
                    )
            elif current_month_start <= date_of_result <= end_of_current_month:
                if date_str in current_month_satisfaction:
                    current_month_satisfaction[date_str] += 1
                else:
                    logging.warning(
                        f"Date {date_str} is out of expected range for current month."
                    )

    return {
        "last_month_daily_satisfaction": last_month_satisfaction,
        "current_month_daily_satisfaction": current_month_satisfaction,
    }
