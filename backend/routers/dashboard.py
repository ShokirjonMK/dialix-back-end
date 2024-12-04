import logging  # noqa: F401
from datetime import datetime

from fastapi.responses import JSONResponse
from fastapi import Depends, APIRouter, status

from backend import db
from backend.schemas import User
from utils.encoder import adapt_json
from backend.services import dashboard as dashboard_service
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency

dashboard_router = APIRouter(tags=["Dashboard"])


@dashboard_router.get("/dashboard")
async def list_dashboard(
    db_session: DatabaseSessionDependency,
    start: datetime,
    end: datetime,
    current_user: User = Depends(get_current_user),
):
    gender_data = dashboard_service.get_gender_data(
        start=start,
        end=end,
        owner_id=current_user.id,
        db=db_session,
    )
    leads_data = dashboard_service.get_leads_data(
        start=start,
        end=end,
        owner_id=current_user.id,
        db=db_session,
    )
    leads_daily = dashboard_service.get_leads_data_daily(
        start, end, current_user.id, db_session
    )
    call_interests_data = dashboard_service.get_call_interests_data(
        start=start,
        end=end,
        owner_id=current_user.id,
        db=db_session,
    )
    operator_data = dashboard_service.get_operator_data(
        start, end, current_user.id, db_session
    )
    sentiment_data = dashboard_service.get_sentiment_analysis_data(
        start, end, current_user.id, db_session
    )
    operator_perfomance_daily = dashboard_service.get_operator_performance_daily(
        start, end, current_user.id, db_session
    )
    call_purpose_data = dashboard_service.get_call_purpose_data(
        start, end, current_user.id, db_session
    )
    call_analytics = dashboard_service.get_call_analytics(
        start, end, current_user.id, db_session
    )

    data = db.get_results(owner_id=str(current_user.id))

    if len(data) == 0:
        return JSONResponse(status_code=status.HTTP_200_OK, content={})

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

    satisfaction_rate_by_month = dashboard_service.calculate_daily_satisfaction(data)

    content = {
        "full_conversations": full_conversations,
        "total_duration": total_duration,
        "total_average_delay": average_delay,
        "total_average_duration": average_duration,
        "total_satisfaction_rate": satisfaction_rate,
        "total_unsatisfaction_rate": unsatisfaction_rate,
        "total_number_of_conversations": number_of_conversations,
        # new
        "gender_data": gender_data,
        "leads_data": leads_data,
        "leads_daily": leads_daily,
        "call_interests_data": call_interests_data,
        "sentiment_data": sentiment_data,
        "operator_data": operator_data,
        "operator_perfomance_daily": operator_perfomance_daily,
        "call_purpose_data": call_purpose_data,
        "call_analytics": call_analytics,
        **satisfaction_rate_by_month,
    }

    return JSONResponse(status_code=status.HTTP_200_OK, content=content)
