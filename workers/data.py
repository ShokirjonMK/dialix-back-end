import asyncio
import json
import logging
import os
from psycopg2.extras import Json
from celery import current_task

import socketio

from workers.common import celery, PredictTask
import backend.db as db
from celery.result import AsyncResult

from backend.sockets import redis_manager

keys_of_interest = [
    "operator_answer_delay",
    "operator_speech_duration",
    "customer_speech_duration",
    "is_conversation_over",
    "sentiment_analysis_of_conversation",
    "sentiment_analysis_of_operator",
    "sentiment_analysis_of_customer",
    "is_customer_satisfied",
    "is_customer_agreed_to_buy",
    "is_customer_interested_to_product",
    "which_course_customer_interested",
    "summary",
    "customer_gender",
]


@celery.task(base=PredictTask, track_started=True, bind=True, acks_late=True)
def upsert_data(self: PredictTask, *args, **kwargs):
    task = kwargs["task"]
    task_id = task["task_id"]
    result_id = task_id.split("/")[-1]
    record_id = task["record_id"]
    owner_id = task["owner_id"]
    is_success = task["is_success"]
    storage_id = task["storage_id"]

    file_path = os.path.join("uploads", storage_id)

    loop = asyncio.get_event_loop()

    existing_record = db.get_record_by_id(record_id, owner_id)
    existing_result = db.get_result_by_record_id(record_id, owner_id)
    existing_result_id = existing_result.get("id", None) if existing_result else None
    task_checklist_id = task.get("checklist_id", None)
    checklist_id = (
        task_checklist_id
        if task_checklist_id
        else (existing_result.get("checklist_id", None) if existing_result else None)
    )

    task = AsyncResult(str(task_id), app=celery)
    task_status = str(task.status)

    if task and is_success and task_status == "SUCCESS":
        task_result = task.result
        general_data = {
            key: existing_result[key]
            for key in keys_of_interest
            if existing_result and key in existing_result
        }

        existing_checklist_response = (
            existing_result.get("checklist_result", {}) if existing_result else {}
        )
        general_response = task_result.get("general_response", general_data)
        checklist_response = (
            task_result.get("checklist_response")
            if task_result.get("checklist_response", None)
            else existing_checklist_response
        )

        db.upsert_record(record={**existing_record, "status": "COMPLETED"})

        if isinstance(checklist_response, str):
            logging.info(f"{checklist_response.strip("`").strip("json").strip("\n")=}")
            checklist_response = json.loads(
                checklist_response.strip("`").strip("json").strip("\n")
            )

        db.upsert_result(
            result={
                "id": str(existing_result_id if existing_result_id else result_id),
                "owner_id": owner_id,
                "record_id": record_id,
                "checklist_id": checklist_id,
                "checklist_result": checklist_response,
                **general_response,
            }
        )

        loop.run_until_complete(
            redis_manager.emit(
                "result",
                {
                    "data": {
                        "record_id": record_id,
                        "result_id": result_id,
                        "checklist_id": checklist_id,
                        "checklist_result": checklist_response,
                        **general_response,
                    }
                },
                room=f"user/{owner_id}",
            )
        )

    else:
        db.upsert_record(
            record={
                **existing_record,
                "status": "FAILED",
            }
        )

        loop.run_until_complete(
            redis_manager.emit(
                "result",
                {
                    "data": {
                        "record_id": record_id,
                        "result_id": result_id,
                        "checklist_id": checklist_id,
                        "status": "FAILED",
                    }
                },
                room=f"user/{owner_id}",
            )
        )

    if os.path.exists(file_path):
        os.remove(file_path)
