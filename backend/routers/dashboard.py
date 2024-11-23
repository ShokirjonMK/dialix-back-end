import math
import logging

from datetime import datetime, timedelta

from fastapi import Depends, APIRouter
from fastapi.responses import JSONResponse

from backend import db
from backend.schemas import User
from utils.encoder import adapt_json
from backend.core.dependencies.user import get_current_user

dashboard_router = APIRouter(tags=["Dashboard"])


@dashboard_router.get("/dashboard")
async def results(current_user: User = Depends(get_current_user)):
    data = db.get_results(owner_id=str(current_user.id))

    if len(data) == 0:
        return JSONResponse(status_code=200, content={})

    data = adapt_json(data)

    full_conversations = (
        (sum(1 for item in data if item["is_conversation_over"])) / len(data)
    ) * 100

    total_duration = sum(item["record_duration"] for item in data)
    total_delay = sum(
        (
            item["operator_answer_delay"]
            if item["operator_answer_delay"] is not None
            else 0
        )
        for item in data
    )

    average_delay = (total_delay / len(data)) / 1000
    average_duration = total_duration / len(data) / 60 / 1000

    satisfied_count = sum(1 for item in data if item["is_customer_satisfied"])
    unsatisfied_count = len(data) - satisfied_count

    satisfaction_rate = (satisfied_count / len(data)) * 100
    unsatisfaction_rate = (unsatisfied_count / len(data)) * 100

    number_of_conversations = db.get_count_of_records(
        owner_id=str(current_user.id)
    ).get("count")
    operator_data = get_operators_data(owner_id=str(current_user.id))

    male_count = sum(1 for item in data if item["customer_gender"] == "male")
    female_count = sum(1 for item in data if item["customer_gender"] == "female")

    satisfaction_rate_by_month = calculate_daily_satisfaction(data)

    content = {
        "full_conversations": full_conversations,
        "total_duration": total_duration,
        "average_delay": average_delay,
        "average_duration": average_duration,
        "satisfaction_rate": satisfaction_rate,
        "unsatisfaction_rate": unsatisfaction_rate,
        "number_of_conversations": number_of_conversations,
        "male_count": male_count,
        "female_count": female_count,
        "operator_data": operator_data,
        **satisfaction_rate_by_month,
    }

    logging.warning(f"Response content: {content}")

    response = JSONResponse(
        status_code=200,
        content=content,
    )

    logging.warning(f"Dashboard data response: {response}")

    return response


def get_operators_data(owner_id):
    operators = db.get_operators(owner_id=str(owner_id))
    number_of_records = db.get_number_records(owner_id=str(owner_id)).get("count", 0)
    result = []

    for operator in operators:
        operator_results = db.get_number_of_operators_records_count(
            owner_id=str(owner_id), operator_code=str(operator["code"])
        ).get("count", 0)
        result.append(
            {
                "operator_code": operator["code"],
                "operator_name": operator["name"],
                "number_of_records": operator_results,
                "number_of_records_percentage": math.floor(
                    (operator_results / number_of_records) * 100
                ),
            }
        )
    return result


def calculate_daily_satisfaction(data):
    # Get the current date and the start dates for the last and current months
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

    # Return the daily satisfaction rates
    return {
        "last_month_daily_satisfaction": last_month_satisfaction,
        "current_month_daily_satisfaction": current_month_satisfaction,
    }
