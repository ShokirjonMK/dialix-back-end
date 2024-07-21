import json
import logging
import os
import uuid
import shutil
import backend.db as db
from typing import Annotated, List, Tuple, Union
from fastapi import Depends, Body, UploadFile, Request, HTTPException
from fastapi.responses import JSONResponse
from backend.app import app
from utils.storage import get_stream_url, upload_file
from utils.audio import generate_waveform, get_audio_duration
from utils.encoder import DateTimeEncoder, adapt_json
from workers.api import api_processing
from backend.auth import get_current_user
from backend.schemas import User, CheckList, ReprocessRecord
from celery.result import AsyncResult
from workers.data import upsert_data

import datetime
from datetime import datetime, timedelta


def get_task_id(user_id):
    task_id = f"{user_id}/{uuid.uuid4()}"
    return task_id


def get_object_storage_id(extension):
    return f"{uuid.uuid4()}.{extension}"


def calculate_daily_satisfaction(data):
    # Get the current date and the start dates for the last and current months
    current_date = datetime.now().date()
    last_month_start = (current_date.replace(day=1) - timedelta(days=1)).replace(day=1)
    end_of_last_month = (current_date.replace(day=1) - timedelta(days=1))
    current_month_start = current_date.replace(day=1)
    end_of_current_month = (current_month_start.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    # Initialize dictionaries to hold satisfaction counts for each day
    last_month_satisfaction = {}
    current_month_satisfaction = {}

    # Generate string formatted dates for keys
    last_month_days = [(last_month_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_of_last_month - last_month_start).days + 1)]
    current_month_days = [(current_month_start + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_of_current_month - current_month_start).days + 1)]

    for day in last_month_days:
        last_month_satisfaction[day] = 0
    for day in current_month_days:
        current_month_satisfaction[day] = 0

    # Distribute satisfaction counts into the respective dictionaries
    for entry in data:
        date_of_result = datetime.strptime(entry["result_created_at"], "%Y-%m-%dT%H:%M:%S.%f").date()
        date_str = date_of_result.strftime("%Y-%m-%d")
        if entry["is_customer_satisfied"]:
            if last_month_start <= date_of_result <= end_of_last_month:
                if date_str in last_month_satisfaction:
                    last_month_satisfaction[date_str] += 1
                else:
                    logging.warning(f"Date {date_str} is out of expected range for last month.")
            elif current_month_start <= date_of_result <= end_of_current_month:
                if date_str in current_month_satisfaction:
                    current_month_satisfaction[date_str] += 1
                else:
                    logging.warning(f"Date {date_str} is out of expected range for current month.")

    # Return the daily satisfaction rates
    return {
        "last_month_daily_satisfaction": last_month_satisfaction,
        "current_month_daily_satisfaction": current_month_satisfaction,
    }


async def process_form_data(request: Request):
    form = await request.form()
    current_user = get_current_user(request)
    files = form.getlist("files")
    general = [gen == "true" for gen in form.getlist("general")]
    checklist_id = [chk if chk else None for chk in form.getlist("checklist_id")]
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0)
    balance = balance if balance is not None else 0
    total_price = 0
    processed_files = []

    for file, gen, chk in zip(files, general, checklist_id):
        storage_id = get_object_storage_id(file.filename.split(".")[-1])
        file_path = os.path.join("uploads", storage_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        duration = get_audio_duration(file_path)

        if duration is None:
            logging.error(f"Error occurred while getting audio duration")
            if os.path.exists(file_path):
                os.remove(file_path)
            return JSONResponse(
                status_code=400, content={"error": "Invalid audio file"}
            )

        processed_files.append(
            {
                "file_path": file_path,
                "duration": duration,
            }
        )

        mohirai_price = (
            duration * db.MOHIRAI_PRICE_PER_MS if gen is True or chk is not None else 0
        )
        general_price = duration * db.GENERAL_PROMPT_PRICE_PER_MS if gen is True else 0
        checklist_price = (
            duration * db.CHECKLIST_PROMPT_PRICE_PER_MS if chk is not None else 0
        )
        total_price += mohirai_price + general_price + checklist_price

    if total_price > balance:
        for file in processed_files:
            if os.path.exists(file["file_path"]):
                os.remove(file["file_path"])
        raise HTTPException(status_code=400, detail="Not enough balance")

    if len(files) != len(general) or len(files) != len(checklist_id):
        raise HTTPException(status_code=400, detail="Mismatched lengths of arrays.")
    return files, general, checklist_id, processed_files


@app.get("/audios_results")
def get_audio_and_results(current_user: User = Depends(get_current_user)):
    recordings = db.get_records(owner_id=str(current_user.id))
    recordings = adapt_json(recordings)
    just_audios = []
    audios_with_checklist = []
    general_audios = []
    full_audios = []
    for record in recordings:
        result = db.get_result_by_record_id(record["id"], owner_id=str(current_user.id))
        audio_url = get_stream_url(f"mohirdev/{record['storage_id']}")
        record["audio_url"] = audio_url
        if result:
            summary = result.get("summary", None)
            checklist_result = result.get("checklist_result", None)
            if summary and checklist_result:
                record["result"] = adapt_json(result)
                full_audios.append(record)
            elif checklist_result:
                record["result"] = adapt_json(result)
                audios_with_checklist.append(record)
            else:
                record["result"] = adapt_json(result)
                general_audios.append(record)
        else:
            record["result"] = None
            just_audios.append(record)
    response = {
        "just_audios": just_audios,
        "audios_with_checklist": audios_with_checklist,
        "general_audios": general_audios,
        "full_audios": full_audios,
        "recordings": recordings,
    }

    return JSONResponse(status_code=200, content=response)


@app.get("/audio/file/{storage_id}")
async def get_audio_file(request: Request, storage_id: str):
    # return url to audio file
    return JSONResponse(
        status_code=200,
        content={"url": f"{request.base_url}uploads/{storage_id}"},
    )
    # return file itself
    # return FileResponse(f"uploads/{storage_id}")


@app.get("/audios_results")
def get_audio_and_results(current_user: User = Depends(get_current_user)):
    recordings = db.get_records(owner_id=str(current_user.id))
    recordings = adapt_json(recordings)
    logging.warning(json.dumps(f"Recordings: {recordings}", indent=2))
    just_audios = []
    audios_with_checklist = []
    general_audios = []
    full_audios = []
    for record in recordings:
        result = db.get_result_by_record_id(record["id"], owner_id=str(current_user.id))
        if result:
            summary = result.get("summary", None)
            checklist_results = result.get("checklist_results", None)
            if summary and checklist_results:
                record["result"] = adapt_json(result)
                full_audios.append(record)
            elif checklist_results:
                record["result"] = adapt_json(result)
                audios_with_checklist.append(record)
            else:
                record["result"] = adapt_json(result)
                general_audios.append(record)
        else:
            record["result"] = None
            just_audios.append(record)
    response = {
        "just_audios": just_audios,
        "audios_with_checklist": audios_with_checklist,
        "general_audios": general_audios,
        "full_audios": full_audios,
        "recordings": recordings,
    }

    return JSONResponse(status_code=200, content=response)


@app.post("/audio", dependencies=[Depends(get_current_user)])
def analyze_data(
    processed_data: Tuple[
        List[UploadFile], List[bool], List[Union[str, None]], List[dict]
    ] = Depends(process_form_data),
    current_user: User = Depends(get_current_user),
):
    responses = []
    files, general, checklist_id, processed_files = processed_data
    for file, general, checklist_id, processed_file in zip(
        files, general, checklist_id, processed_files
    ):
        record_id = str(uuid.uuid4())
        owner_id = str(current_user.id)
        status = "UPLOADED" if general is False and checklist_id is None else "PENDING"
        storage_id = processed_file["file_path"].split("/")[-1]
        file_path = processed_file["file_path"]
        duration = processed_file["duration"]
        bucket = os.getenv("STORAGE_BUCKET_NAME", "dialixai-production")

        upload_file(bucket, f"mohirdev/{storage_id}", file_path)

        task_id = get_task_id(user_id=current_user.id)

        record = {
            "id": record_id,
            "owner_id": owner_id,
            "title": file.filename,
            "status": status,
            "duration": duration * 1000,
            "storage_id": storage_id,
        }

        audio_record = db.upsert_record(
            record=record,
        )

        logging.warning(
            f"Audio record: {audio_record} with id: {record_id} and owner_id: {current_user.id}"
        )

        audio_local_path = f"uploads/transcode_{storage_id}.mp3"

        waveform_local_path = f"uploads/transcode_waveform_{storage_id}.dat"

        # generate_waveform(audio_local_path, waveform_local_path)

        if general is False and checklist_id is None:
            responses.append(
                {
                    "id": task_id,
                    "record_id": record_id,
                    "record_title": file.filename,
                    "status": status,
                    "duration": duration * 1000,
                    "storage_id": storage_id,
                }
            )
            if os.path.exists(file_path):
                os.remove(file_path)
            continue

        task: AsyncResult = api_processing.apply_async(
            kwargs={
                "task": {
                    "audio_record": audio_record,
                    "checklist_id": checklist_id,
                    "general": general,
                },
            },
            link=upsert_data.s(
                task={
                    "task_id": task_id,
                    "owner_id": owner_id,
                    "record_id": audio_record["id"],
                    "checklist_id": checklist_id,
                    "storage_id": audio_record["storage_id"],
                    "is_success": True,
                }
            ).set(queue="data"),
            link_error=upsert_data.s(
                task={
                    "task_id": task_id,
                    "owner_id": owner_id,
                    "record_id": audio_record["id"],
                    "checklist_id": checklist_id,
                    "storage_id": audio_record["storage_id"],
                    "is_success": False,
                }
            ).set(queue="data"),
            queue="api",
            task_id=task_id,
        )

        responses.append(
            {
                "id": task.id,
                "record_id": record_id,
                "checklist_id": checklist_id,
                "record_title": file.filename,
                "status": status,
                "duration": duration * 1000,
                "storage_id": storage_id,
            }
        )

    return JSONResponse(status_code=200, content=responses)


@app.post("/reprocess")
def reprocess_data(
    record: ReprocessRecord,
    current_user: User = Depends(get_current_user),
):
    record_id = record.record_id
    checklist_id = record.checklist_id
    general = record.general
    existing_record = db.get_record_by_id(record_id, owner_id=str(current_user.id))
    if not existing_record:
        return JSONResponse(status_code=404, content={"error": "Record not found"})

    record = {
        **existing_record,
        "status": "PENDING",
    }
    db.upsert_record(record=record)

    task_id = get_task_id(user_id=current_user.id)

    task: AsyncResult = api_processing.apply_async(
        kwargs={
            "task": {
                "audio_record": record,
                "checklist_id": checklist_id,
                "general": general,
            },
        },
        link=upsert_data.s(
            task={
                "task_id": task_id,
                "owner_id": str(current_user.id),
                "record_id": record_id,
                "checklist_id": checklist_id,
                "storage_id": record["storage_id"],
                "is_success": True,
            }
        ).set(queue="data"),
        link_error=upsert_data.s(
            task={
                "task_id": task_id,
                "owner_id": str(current_user.id),
                "record_id": record_id,
                "checklist_id": checklist_id,
                "storage_id": record["storage_id"],
                "is_success": False,
            }
        ).set(queue="data"),
        queue="api",
        task_id=task_id,
    )

    response_data = {
        "id": task.id,
        "status": "PENDING",
    }

    return JSONResponse(status_code=200, content=response_data)


@app.get("/dashboard")
def results(current_user: User = Depends(get_current_user)):
    data = db.get_results(owner_id=str(current_user.id))

    if not data:
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
    average_duration = total_duration / len(data)

    satisfied_count = sum(1 for item in data if item["is_customer_satisfied"])
    unsatisfied_count = len(data) - satisfied_count

    satisfaction_rate = (satisfied_count / len(data)) * 100
    unsatisfaction_rate = (unsatisfied_count / len(data)) * 100

    number_of_conversations = db.get_count_of_records(
        owner_id=str(current_user.id)
    ).get("count")

    male_count = sum(1 for item in data if item["customer_gender"] == "male")
    female_count = sum(1 for item in data if item["customer_gender"] == "female")

    satisfaction_rate_by_month = (
        calculate_daily_satisfaction(data)
    )

    return JSONResponse(
        status_code=200,
        content={
            "full_conversations": full_conversations,
            "total_duration": total_duration,
            "average_delay": average_delay,
            "average_duration": average_duration,
            "satisfaction_rate": satisfaction_rate,
            "unsatisfaction_rate": unsatisfaction_rate,
            "number_of_conversations": number_of_conversations,
            "male_count": male_count,
            "female_count": female_count,
            **satisfaction_rate_by_month,
        },
    )


@app.get("/audios/pending")
def get_pending_audios(current_user: User = Depends(get_current_user)):
    data = db.get_pending_audios(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)


@app.post("/checklist")
def upsert_checklist(
    data: CheckList,
    current_user: User = Depends(get_current_user),
):
    id = str(data.id)
    title = data.title
    payload = json.dumps(data.payload)
    deleted_at = data.deleted_at
    active = data.active
    checklist = {
        "id": id,
        "title": title,
        "payload": payload,
        "active": active,
        "deleted_at": deleted_at,
        "owner_id": str(current_user.id),
    }
    result = db.upsert_checklist(checklist=checklist)
    response = adapt_json(result)
    return JSONResponse(status_code=200, content=response)


@app.post("/activate_checklist")
def activate_checklist(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    result = db.activate_checklist(checklist_id, owner_id=str(current_user.id))
    if result:
        return JSONResponse(status_code=200, content={"success": True})
    return JSONResponse(status_code=404, content={"error": "Not found"})


@app.get("/checklists")
def get_list_of_checklists(current_user: User = Depends(get_current_user)):
    data = db.get_checklists(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)


@app.get("/checklist/{checklist_id}")
def get_checklist_by_id(
    checklist_id: str, current_user: User = Depends(get_current_user)
):
    data = db.get_checklist_by_id(checklist_id, owner_id=str(current_user.id))
    if data:
        data = adapt_json(data)
        return JSONResponse(status_code=200, content=data)
    return JSONResponse(status_code=404, content={"error": "Not found"})


# TODO: add logic to remove all results related to the check list
@app.delete("/checklist/{checklist_id}")
def delete_checklist(checklist_id: str, current_user: User = Depends(get_current_user)):
    result = db.delete_checklist(checklist_id, owner_id=str(current_user.id))
    if result:
        return JSONResponse(status_code=200, content={"success": True})
    return JSONResponse(status_code=404, content={"error": "Not found"})
