import logging
from datetime import datetime
from typing import List, Dict

from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract, join

from backend.database.models import Record, Result


def get_monthly_data(db_session: Session, start, end, owner_id):
    stmt = (
        select(
            func.date_trunc("day", Record.created_at).label("day"),
            func.count(Record.id).label("total_calls"),
        )
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(func.date_trunc("day", Record.created_at))
        .order_by("day")
    )
    result = db_session.execute(stmt)
    return [
        {"day": row.day.strftime("%Y-%m-%d"), "calls": row.total_calls}
        for row in result
    ]


def get_weekly_data(db_session: Session, start, end, owner_id):
    stmt = (
        select(
            extract("dow", Record.created_at).label("day_of_week"),
            func.count(Record.id).label("total_calls"),
        )
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(extract("dow", Record.created_at))
        .order_by("day_of_week")
    )
    result = db_session.execute(stmt)
    return [
        {"day_of_week": int(row.day_of_week), "calls": row.total_calls}
        for row in result
    ]


def get_daily_data(db_session: Session, start, end, owner_id):
    stmt = (
        select(
            extract("hour", Record.created_at).label("hour"),
            func.count(Record.id).label("total_calls"),
        )
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(extract("hour", Record.created_at))
        .order_by("hour")
    )
    result = db_session.execute(stmt)
    return [{"hour": int(row.hour), "calls": row.total_calls} for row in result]


def get_gender_data(
    start: datetime, end: datetime, owner_id: str, db: Session
) -> Dict[str, List[Dict]]:
    # Join Record and Result tables to include customer_gender
    record_result_join = select(Result, Record).select_from(
        join(Record, Result, Record.id == Result.record_id)
    )

    # Daily Data Query
    daily_query = (
        select(
            func.date_trunc("day", Record.created_at).label("date"),
            Result.customer_gender,
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(func.date_trunc("day", Record.created_at), Result.customer_gender)
        .order_by("date")
    )

    daily_results = db.execute(daily_query)
    daily_data = process_daily_data(daily_results.fetchall())

    logging.info(f"{daily_results.all()=}")

    # Weekly Data Query
    weekly_query = (
        select(
            func.to_char(Record.created_at, "IW").label("week"),
            Result.customer_gender,
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(func.to_char(Record.created_at, "IW"), Result.customer_gender)
        .order_by("week")
    )

    weekly_results = db.execute(weekly_query)
    weekly_data = process_weekly_data(weekly_results.fetchall())

    # Monthly Data Query
    monthly_query = (
        select(
            func.to_char(Record.created_at, "Mon YYYY").label("month"),
            Result.customer_gender,
            func.count(Record.id).label("count"),
        )
        .select_from(record_result_join)
        .where(Record.owner_id == owner_id, Record.created_at.between(start, end))
        .group_by(func.to_char(Record.created_at, "Mon YYYY"), Result.customer_gender)
        .order_by("month")
    )

    monthly_results = db.execute(monthly_query)
    monthly_data = process_monthly_data(monthly_results.fetchall())

    return {"daily": daily_data, "weekly": weekly_data, "monthly": monthly_data}


def process_daily_data(results: List[tuple]) -> List[Dict]:
    daily_data = {}
    for date, gender, count in results:
        date_str = date.strftime("%Y-%m-%d")
        if date_str not in daily_data:
            daily_data[date_str] = {"male": 0, "female": 0}
        daily_data[date_str][gender] += count

    formatted_daily_data = [
        {
            "date": date,
            "male": {
                "count": data["male"],
                "percentage": calculate_percentage(data["male"], sum(data.values())),
            },
            "female": {
                "count": data["female"],
                "percentage": calculate_percentage(data["female"], sum(data.values())),
            },
        }
        for date, data in daily_data.items()
    ]
    return formatted_daily_data


def process_weekly_data(results: List[tuple]) -> List[Dict]:
    weekly_data = {}
    for week, gender, count in results:
        if week not in weekly_data:
            weekly_data[week] = {"male": 0, "female": 0}
        weekly_data[week][gender] += count

    formatted_weekly_data = [
        {
            "period": f"Week {week}",
            "male": {
                "count": data["male"],
                "percentage": calculate_percentage(data["male"], sum(data.values())),
            },
            "female": {
                "count": data["female"],
                "percentage": calculate_percentage(data["female"], sum(data.values())),
            },
        }
        for week, data in weekly_data.items()
    ]
    return formatted_weekly_data


def process_monthly_data(results: List[tuple]) -> List[Dict]:
    monthly_data = {}
    for month, gender, count in results:
        if month not in monthly_data:
            monthly_data[month] = {"male": 0, "female": 0}
        monthly_data[month][gender] += count

    formatted_monthly_data = [
        {
            "period": month,
            "male": {
                "count": data["male"],
                "percentage": calculate_percentage(data["male"], sum(data.values())),
            },
            "female": {
                "count": data["female"],
                "percentage": calculate_percentage(data["female"], sum(data.values())),
            },
        }
        for month, data in monthly_data.items()
    ]
    return formatted_monthly_data


def calculate_percentage(part: int, whole: int) -> int:
    return round((part / whole) * 100) if whole else 0
