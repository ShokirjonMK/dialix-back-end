import os
import uuid
import math
import shutil
import logging
import typing as t  # noqa: F401
from decouple import config
from datetime import datetime, timedelta
from typing import List, Tuple, Union, Optional

from celery.result import AsyncResult

from fastapi.responses import JSONResponse
from fastapi import Depends, UploadFile, Request, HTTPException, APIRouter, status

from backend import db
from backend.core.auth import get_current_user
from backend.schemas import (
    User,
    ReprocessRecord,
    OperatorData,
    RecordQueryParams,
    ResultQueryParams,
)

from utils.storage import get_stream_url, upload_file
from utils.audio import get_audio_duration
from utils.encoder import adapt_json
from utils.data_manipulation import (
    find_operator_code,
    find_call_type,
    get_phone_number_from_filename,
)
from workers.api import api_processing
from workers.data import upsert_data
from backend.utils.validators import validate_filename
from backend.core.dependencies import DatabaseSessionDependency


api_router = APIRouter()


def generate_task_id(user_id) -> str:
    return f"{user_id}/{uuid.uuid4()}"


def get_object_storage_id(extension):
    return f"{uuid.uuid4()}.{extension}"


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


async def process_form_data(request: Request, db_session: DatabaseSessionDependency):
    form = await request.form()
    current_user = get_current_user(request, db_session)
    files = form.getlist("files")
    logging.info(f"{files=}")
    general = [gen == "true" for gen in form.getlist("general")]
    checklist_id = [chk if chk else None for chk in form.getlist("checklist_id")]
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0)
    balance = balance if balance is not None else 0
    total_price = 0
    processed_files = []

    for file, gen, chk in zip(files, general, checklist_id):
        if not validate_filename(file.file):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Filename format is wrong. It should be like '23.10.04-05:08:37_102_933040598.mp3'",
            )

        storage_id = get_object_storage_id(file.filename.split(".")[-1])
        file_path = os.path.join("uploads", storage_id)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        duration = get_audio_duration(file_path)

        if duration is None:
            logging.error("Error occurred while getting audio duration")
            if os.path.exists(file_path):
                os.remove(file_path)
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"error": "Invalid audio file"},
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

    logging.info(f"Process form data: {total_price=} {balance=}")

    if total_price > balance:
        for file in processed_files:
            if os.path.exists(file["file_path"]):
                os.remove(file["file_path"])
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="Not enough balance"
        )

    if len(files) != len(general) or len(files) != len(checklist_id):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Mismatched lengths of arrays.",
        )

    return files, general, checklist_id, processed_files


@api_router.get("/audios_results")
async def get_audio_and_results(
    current_user: User = Depends(get_current_user),
    record_query_params: RecordQueryParams = Depends(),
    result_query_params: ResultQueryParams = Depends(),
):
    record_filter_params = record_query_params.model_dump(
        mode="python", exclude_none=True
    )
    result_filter_params = result_query_params.model_dump(
        mode="python", exclude_none=True
    )
    logging.info(f"{record_filter_params=} {result_filter_params=}")

    recordings = db.get_records_v1(
        owner_id=str(current_user.id), filter_params=record_filter_params
    )
    recordings = adapt_json(recordings)

    logging.info(f"{recordings=}")

    full_audios = []
    just_audios = []
    general_audios = []
    audios_with_checklist = []

    folder_name = current_user.company_name.lower().replace(" ", "_")

    for record in recordings:
        result = db.get_result_by_record_id(
            record["id"],
            owner_id=str(current_user.id),
            filter_params=result_filter_params,
        )
        logging.info(f"{result=} for {record=}")

        if result_filter_params:
            if result is None:
                """if filters are being applied, and 
                results is NONE then
                we don't include this recording
                """
                continue

        audio_url = get_stream_url(f"{folder_name}/{record['storage_id']}")
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

    return JSONResponse(status_code=status.HTTP_200_OK, content=response)


@api_router.get("/v2/audios_results")
async def get_audio_and_results_v2(current_user: User = Depends(get_current_user)):
    recordings = db.get_records_v2(owner_id=str(current_user.id))

    recordings = adapt_json(recordings)
    folder_name = current_user.company_name.lower().replace(" ", "_")

    for record in recordings:
        result = db.get_result_by_record_id(record["id"], owner_id=str(current_user.id))
        audio_url = get_stream_url(f"{folder_name}/{record['storage_id']}")

        record["audio_url"] = audio_url

        if not result:
            record["type"] = "just_audio"
            record["result"] = None
        else:
            summary_exists: bool = result.get("summary") is not None
            checklist_result_exists: bool = result.get("checklist_result") is not None

            if summary_exists and checklist_result_exists:
                record["type"] = "full_audio"
            elif checklist_result_exists:
                record["type"] = "audio_with_checklist"
            else:
                record["type"] = "general_audio"

            record["result"] = adapt_json(result)

    return JSONResponse(status_code=status.HTTP_200_OK, content=recordings)


@api_router.get("/audio/file/{storage_id}")
async def get_audio_file(request: Request, storage_id: str):
    # return url to audio file
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"url": f"{request.base_url}uploads/{storage_id}"},
    )
    # or file itself
    # return FileResponse(f"uploads/{storage_id}")


@api_router.post("/audio", dependencies=[Depends(get_current_user)])
async def analyze_data(
    processed_data: Tuple[
        List[UploadFile], List[bool], List[Union[str, None]], List[dict]
    ] = Depends(process_form_data),
    current_user: User = Depends(get_current_user),
    _operator_code: Optional[str] = None,  # for now, internal use only
    _call_type: Optional[str] = None,  # for now, internal use only
    _destination_number: Optional[str] = None,  # for now, internal use only
):
    responses = []

    files, general, checklist_id, processed_files = processed_data

    logging.info(
        f"Received request: {files=} {general=} {checklist_id=} {processed_files=}"
    )

    for file, general, checklist_id, processed_file in zip(
        files, general, checklist_id, processed_files
    ):
        record_id = str(uuid.uuid4())
        owner_id = str(current_user.id)
        status = "UPLOADED" if general is False and checklist_id is None else "PENDING"
        storage_id = processed_file["file_path"].split("/")[-1]
        file_path = processed_file["file_path"]
        duration = processed_file["duration"]
        bucket = config("STORAGE_BUCKET_NAME", default="dialixai-production")

        folder_name = current_user.company_name.lower().replace(" ", "_")

        upload_file(bucket, f"{folder_name}/{storage_id}", file_path)
        logging.info(
            f"folder_name: {folder_name} storage_id: {storage_id}, bucket: {bucket}"
        )
        task_id = generate_task_id(user_id=current_user.id)

        operator_code = _operator_code or find_operator_code(file.filename)
        call_type = _call_type or find_call_type(file.filename)
        client_phone_number = _destination_number or get_phone_number_from_filename(
            file.filename
        )

        logging.info(
            f"Metadata: {_operator_code=} {_call_type=} {_destination_number=}"
            f" => {operator_code=} {call_type=} {client_phone_number}"
        )

        operator = (
            db.get_operator_name_by_code(owner_id=owner_id, code=operator_code) or {}
        )
        operator_name = operator.get("name", None)

        record = {
            "id": record_id,
            "owner_id": owner_id,
            "title": file.filename,
            "operator_code": operator_code,
            "operator_name": operator_name,
            "call_type": call_type,
            "status": status,
            "duration": duration * 1000,
            "storage_id": storage_id,
            "client_phone_number": client_phone_number,
        }

        audio_record = db.upsert_record(record=record)

        logging.warning(
            f"Audio record: {audio_record} with id: {record_id} and owner_id: {current_user.id}"
        )

        # audio_local_path = f"uploads/transcode_{storage_id}.mp3"
        # waveform_local_path = f"uploads/transcode_waveform_{storage_id}.dat"
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
                    "folder_name": folder_name,
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


@api_router.post("/reprocess")
async def reprocess_data(
    record: ReprocessRecord,
    current_user: User = Depends(get_current_user),
):
    record_id = record.record_id
    checklist_id = record.checklist_id
    general = record.general
    folder_name = current_user.company_name.lower().replace(" ", "_")
    existing_record = db.get_record_by_id(record_id, owner_id=str(current_user.id))
    if not existing_record:
        return JSONResponse(status_code=404, content={"error": "Record not found"})

    # count the price
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0)
    balance = balance if balance is not None else 0
    total_price = 0
    duration = existing_record["duration"]
    mohirai_price = (
        duration * db.MOHIRAI_PRICE_PER_MS if existing_record["payload"] is None else 0
    )
    general_price = duration * db.GENERAL_PROMPT_PRICE_PER_MS if general is True else 0
    checklist_price = (
        duration * db.CHECKLIST_PROMPT_PRICE_PER_MS if checklist_id is not None else 0
    )
    total_price += mohirai_price + general_price + checklist_price

    if total_price > balance:
        return JSONResponse(status_code=400, content={"error": "Not enough balance"})

    record = {
        **existing_record,
        "status": "PENDING",
    }
    db.upsert_record(record=record)

    task_id = generate_task_id(user_id=current_user.id)

    task: AsyncResult = api_processing.apply_async(
        kwargs={
            "task": {
                "audio_record": record,
                "checklist_id": checklist_id,
                "general": general,
                "folder_name": folder_name,
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


@api_router.get("/dashboard")
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


@api_router.get("/audios/pending")
async def get_pending_audios(current_user: User = Depends(get_current_user)):
    data = db.get_pending_audios(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)


@api_router.post("/operator")
async def upsert_operator(
    data: OperatorData,
    current_user: User = Depends(get_current_user),
):
    operator_code = data.code
    operator_name = data.name
    deleted_at = data.deleted_at
    operator = {
        "id": str(data.id),
        "owner_id": str(current_user.id),
        "code": int(operator_code),
        "name": operator_name,
        "deleted_at": deleted_at,
    }
    result = db.upsert_operator(operator=operator)
    response = adapt_json(result)
    return JSONResponse(status_code=200, content=response)


@api_router.get("/operators")
async def get_list_of_operators(current_user: User = Depends(get_current_user)):
    data = db.get_operators(owner_id=str(current_user.id))
    data = adapt_json(data)
    return JSONResponse(status_code=200, content=data)
