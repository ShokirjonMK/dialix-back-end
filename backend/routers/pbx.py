import logging
import typing as t

import httpx
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from backend.core import settings
from backend.api import analyze_data

from backend.schemas import User, PBXCallHistoryRequest
from backend.utils.pbx import (
    download_from,
    get_call_info_by,
    get_call_download_url,
    filter_calls,
)
from backend.services.operator import create_operators
from backend.core.dependencies import (
    DatabaseSessionDependency,
    PbxCredentialsDependency,
    get_current_user,
)

pbx_router = APIRouter(tags=["PBX Integration"])


@pbx_router.get("/pbx_operators")
async def get_users(pbx_credentials: PbxCredentialsDependency):
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/user/get.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        response_data = response.json()

        if response_data["status"] != "1":
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return JSONResponse(content=response_data, status_code=status.HTTP_200_OK)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {exc}",
        )


@pbx_router.post("/sync_operators")
async def sync_operators(
    db_session: DatabaseSessionDependency,
    pbx_credentials: PbxCredentialsDependency,
    current_user: User = Depends(get_current_user),
):
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/user/get.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            )

        response_data = response.json()

        if response_data["status"] != "1":
            raise HTTPException(status_code=response.status_code, detail=response.text)

        operators_data: list[dict] = [
            {
                "name": operator.get("name"),
                "code": int(operator.get("num")),
                "owner_id": current_user.id,
            }
            for operator in response_data["data"]
        ]

        create_operators(db_session, operators_data)

        return JSONResponse(
            content={
                "success": True,
                "message": f"Total {len(operators_data)} were added",
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing operators: {exc}",
        )


@pbx_router.get("/history")
async def list_call_history(
    pbx_credentials: PbxCredentialsDependency,
    start_stamp_from: str,
    end_stamp_to: str,
):
    logging.info("Preparing and sending request ...")
    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/mongo_history/search.json"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                headers={
                    "x-pbx-authentication": f"{pbx_credentials.key_id}:{pbx_credentials.key}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "start_stamp_from": start_stamp_from,
                    "end_stamp_to": end_stamp_to,
                },
            )
            logging.info(f"Response arrived: {response.status_code=}")

        response.raise_for_status()
        json_response = response.json()

        if int(json_response["status"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=json_response["comment"],
            )

        logging.info(f"Total number of calls is {len(json_response['data'])}")

        filtered_calls = filter_calls(json_response["data"])
        logging.info(f"Number of filtered calls: {len(filtered_calls)}")

        return JSONResponse(content=filtered_calls, status_code=status.HTTP_200_OK)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching call history: {exc}",
        )


@pbx_router.post("/history")
async def process_from_call_history(
    request: PBXCallHistoryRequest,
    pbx_credentials: PbxCredentialsDependency,
    current_user: User = Depends(get_current_user),
):
    data = request.model_dump(exclude_none=True)

    url = f"{settings.PBX_API_URL.format(domain=pbx_credentials.domain)}/mongo_history/search.json"

    try:
        call_info_response = await get_call_info_by(
            request.uuid, url, pbx_credentials.key_id, pbx_credentials.key
        )
        if int(call_info_response["status"]) == 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=call_info_response["comment"],
            )

        call_info = call_info_response["data"][0]
        download_url_response = await get_call_download_url(
            data, url, pbx_credentials.key_id, pbx_credentials.key
        )

        if call_info["user_talk_time"] == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User did not say any word, and we need to analyze that?",
            )

        download_url = download_url_response.get("data")

        filename = f"call-{request.uuid}.mp3"
        download_file_path = f"./audios/{filename}"

        downloaded_file = await download_from(download_url, download_file_path)
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
            _destination_number=call_info["destination_number"],
        )

        logging.info(f"Analysis endpoint's {response.status_code=} {response.body=}")

        return response

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing call history: {exc}",
        )
