import logging
import typing as t

import requests

from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.core import settings
from backend.api import analyze_data
from backend.core.auth import get_current_user
from backend.schemas import User, PBXCallHistoryRequest
from backend.utils.pbx import (
    download_from,
    get_call_info_by,
    get_call_download_url,
    paginate_response,
    filter_calls,
)

pbx_router = APIRouter(tags=["PBX Integration"])


@pbx_router.post("/auth/{domain}")
async def authenticate(domain: str, api_key: str):
    url = f"{settings.PBX_API_URL.format(domain=domain)}/auth.json"

    try:
        response = requests.post(
            url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            data={"auth_key": api_key},
        )

        if response.status_code == status.HTTP_200_OK:
            return JSONResponse(
                status_code=response.status_code, content=response.json()
            )
        raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error on authenticating to PBX: {exc}",
        )


@pbx_router.post("/users/{domain}")
async def get_users(domain: str, key_id: str, key: str):
    url = f"{settings.PBX_API_URL.format(domain=domain)}/user/get.json"

    try:
        response = requests.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            return JSONResponse(
                status_code=response.status_code, content=response.json()
            )
        raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {exc}",
        )


@pbx_router.post("/groups/{domain}")
def get_groups(domain: str, key_id: str, key: str):
    url = f"{settings.PBX_API_URL.format(domain=domain)}/group/get.json"

    try:
        response = requests.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        if response.status_code == status.HTTP_200_OK:
            return JSONResponse(
                status_code=response.status_code, content=response.json()
            )
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {exc}",
        )


@pbx_router.get("/history/{domain}")
async def list_call_history(
    domain: str,
    key_id: str,
    key: str,
    start_stamp_from: str,
    end_stamp_to: str,
    page_number: int,
    page_size: t.Optional[int] = 10,
):
    url = f"{settings.PBX_API_URL.format(domain=domain)}/mongo_history/search.json"

    response = requests.post(
        url,
        headers={
            "x-pbx-authentication": f"{key_id}:{key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"start_stamp_from": start_stamp_from, "end_stamp_to": end_stamp_to},
    )
    response.raise_for_status()
    json_response = response.json()
    if int(json_response["status"]) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=json_response["comment"]
        )

    logging.info(f"Total number of calls is {len(json_response['data'] )}")

    filtered_calls = filter_calls(json_response["data"])
    logging.info(f"Number of filtered calls: {len(filtered_calls)}")

    response_content = paginate_response(filtered_calls, page_number, page_size)

    return JSONResponse(content=response_content, status_code=status.HTTP_200_OK)


@pbx_router.post("/history/{domain}")
async def process_from_call_history(
    request: PBXCallHistoryRequest,
    domain: str,
    key_id: str,
    key: str,
    current_user: User = Depends(get_current_user),
):
    data = request.model_dump(exclude_none=True)

    url = f"{settings.PBX_API_URL.format(domain=domain)}/mongo_history/search.json"

    call_info_response = get_call_info_by(request.uuid, url, key_id, key)
    if int(call_info_response["status"]) == 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=call_info_response["comment"],
        )

    call_info = call_info_response["data"][0]
    download_url_response = get_call_download_url(data, url, key_id, key)

    if call_info["user_talk_time"] == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User did not say any word, and we need to analyse that?",
        )

    download_url = download_url_response.get("data")

    filename = f"call-{request.uuid}.mp3"
    download_file_path = f"./audios/{filename}"

    downloaded_file = download_from(download_url, download_file_path)
    logging.info(f"Downloaded file path: {downloaded_file}")

    with open(downloaded_file, "rb") as audio_file:
        upload_file = UploadFile(audio_file, filename=filename)

    processed_data = (
        [upload_file],
        [True],
        [request.checklist_id],
        [{"file_path": download_file_path, "duration": call_info["duration"]}],
    )

    logging.info(f"Preparing: {processed_data=}")

    response = await analyze_data(
        processed_data=processed_data,
        current_user=current_user,
        _operator_code=call_info["caller_id_number"],
        _call_type=call_info["accountcode"],
    )
    logging.info(f"Analysis endpoint's {response.status_code=} {response.body=}")

    return response
