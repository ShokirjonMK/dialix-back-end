import os
import uuid
import math
import json
import shutil
import logging
import tarfile
from typing import List, Tuple, Union
from datetime import datetime, timedelta

import requests

from celery.result import AsyncResult

from fastapi import Depends, UploadFile, Request, HTTPException, APIRouter
from fastapi.responses import JSONResponse

from backend import db
from backend.core.auth import get_current_user
from backend.schemas import User, ReprocessRecord, OperatorData, CallHistoryRequest

from utils.storage import get_stream_url, upload_file
from utils.audio import get_audio_duration
from utils.encoder import adapt_json
from utils.data_manipulation import find_operator_code, find_call_type

from workers.api import api_processing
from workers.data import upsert_data


api_router = APIRouter()

PBX_URL = "https://api.onlinepbx.ru/{domain}"

MAX_FILE_SIZE_MB = 15
SUPPORTED_FORMATS = [".mp3", ".wav", ".aac"]


def get_task_id(user_id):
    task_id = f"{user_id}/{uuid.uuid4()}"
    return task_id


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


async def process_form_data(request: Request):
    form = await request.form()
    current_user = await get_current_user(request)
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
            logging.error("Error occurred while getting audio duration")
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


@api_router.get("/audios_results")
async def get_audio_and_results(current_user: User = Depends(get_current_user)):
    recordings = db.get_records(owner_id=str(current_user.id))
    recordings = adapt_json(recordings)
    just_audios = []
    audios_with_checklist = []
    general_audios = []
    full_audios = []
    folder_name = current_user.company_name.lower().replace(" ", "_")
    for record in recordings:
        result = db.get_result_by_record_id(record["id"], owner_id=str(current_user.id))
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

    return JSONResponse(status_code=200, content=response)


@api_router.get("/audio/file/{storage_id}")
async def get_audio_file(request: Request, storage_id: str):
    # return url to audio file
    return JSONResponse(
        status_code=200,
        content={"url": f"{request.base_url}uploads/{storage_id}"},
    )
    # return file itself
    # return FileResponse(f"uploads/{storage_id}")


@api_router.get("/audios_results")
async def get_audio_and_results(current_user: User = Depends(get_current_user)):
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


@api_router.post("/audio", dependencies=[Depends(get_current_user)])
async def analyze_data(
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

        folder_name = current_user.company_name.lower().replace(" ", "_")

        upload_file(bucket, f"{folder_name}/{storage_id}", file_path)
        logging.warning(
            f"folder_name: {folder_name} storage_id: {storage_id}, bucket: {bucket}"
        )
        task_id = get_task_id(user_id=current_user.id)
        operator_code = find_operator_code(file.filename)
        call_type = find_call_type(file.filename)
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

    task_id = get_task_id(user_id=current_user.id)

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


@api_router.post("/auth/{domain}")
def authenticate(domain: str, api_key: str):
    url = PBX_URL.format(domain=domain)
    data = {"auth_key": api_key}

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }

    try:
        response = requests.post(f"{url}/auth.json", headers=headers, data=data)

        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error authenticating: {str(e)}")


@api_router.post("/users/{domain}")
def get_users(domain: str, key_id: str, key: str):
    headers = {
        "x-pbx-authentication": f"{key_id}:{key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            f"{PBX_URL.format(domain=domain)}/user/get.json", headers=headers
        )

        if response.status_code == 200:
            json_response = response.json()

            return JSONResponse(status_code=200, content=json_response)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching call history: {str(e)}"
        )


@api_router.post("/groups/{domain}")
def get_groups(domain: str, key_id: str, key: str):
    headers = {
        "x-pbx-authentication": f"{key_id}:{key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            f"{PBX_URL.format(domain=domain)}/group/get.json", headers=headers
        )

        if response.status_code == 200:
            json_response = response.json()

            return JSONResponse(status_code=200, content=json_response)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching call history: {str(e)}"
        )


def download_tar_file(url: str, save_path: str) -> str:
    """
    Downloads the tar file from the given URL and saves it to the specified path.

    :param url: URL to download the tar file from
    :param save_path: Path to save the downloaded tar file
    :return: Path to the saved tar file
    """
    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        response = requests.get(url, stream=True)
        response.raise_for_status()

        # Save the file
        with open(save_path, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return save_path
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error downloading tar file: {str(e)}"
        )


def extract_tar_file(tar_path: str, extract_to: str) -> None:
    """
    Extracts the contents of a tar file to the specified directory.

    :param tar_path: Path to the tar file
    :param extract_to: Directory to extract the tar file contents
    """
    try:
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(path=extract_to)
    except (tarfile.TarError, IOError) as e:
        raise HTTPException(
            status_code=500, detail=f"Error extracting tar file: {str(e)}"
        )


@api_router.post("/history/{domain}")
def get_calls_history(
    request: CallHistoryRequest,
    domain: str,
    key_id: str,
    key: str,
    current_user: User = Depends(get_current_user),
):
    data = request.dict(exclude_none=True)

    headers = {
        "x-pbx-authentication": f"{key_id}:{key}",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        response = requests.post(
            f"{PBX_URL.format(domain=domain)}/mongo_history/search.json",
            headers=headers,
            data=data,
        )

        if response.status_code == 200:
            json_response = response.json()

            download_url = json_response.get("data")
            if isinstance(download_url, str):
                tar_file_path = "./tmp/calls.tar"
                extract_dir = "./audios"
                os.makedirs(extract_dir, exist_ok=True)
                downloaded_file = download_tar_file(download_url, tar_file_path)
                extract_tar_file(downloaded_file, extract_dir)
                extracted_files = os.listdir(extract_dir)

                audio_folder = "./audios"
                files_to_send = []
                processed_files = []

                for filename in extracted_files:
                    file_path = os.path.join(audio_folder, filename)

                    if os.path.exists(file_path):
                        with open(file_path, "rb") as audio_file:
                            upload_file = UploadFile(audio_file, filename=filename)
                            files_to_send.append(upload_file)

                        processed_files.append({"file_path": file_path, "duration": 0})

                processed_data = (
                    files_to_send,
                    [False] * len(files_to_send),
                    [None] * len(files_to_send),
                    processed_files,
                )
                response = analyze_data(
                    processed_data=processed_data, current_user=current_user
                )

                try:
                    for filename in extracted_files:
                        file_path = os.path.join(extract_dir, filename)
                        if os.path.exists(file_path):
                            os.remove(file_path)

                    if os.path.exists(tar_file_path):
                        os.remove(tar_file_path)
                except Exception as cleanup_error:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error during cleanup: {str(cleanup_error)}",
                    )

                return response
            else:
                return JSONResponse(status_code=200, content=json_response)
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching call history: {str(e)}"
        )
