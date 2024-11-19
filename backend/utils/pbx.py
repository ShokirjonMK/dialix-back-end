import httpx
import logging
import tarfile
import requests
import typing as t
from uuid import UUID

from fastapi import HTTPException, status

from backend.core import settings


async def download_from(url: str, file_path: str) -> str:
    async with httpx.AsyncClient() as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            with open(file_path, "wb") as file:
                async for chunk in response.aiter_bytes():
                    file.write(chunk)
            logging.info(f"File downloaded successfully: {file_path}")
    return file_path


def extract_tar_file(tar_path: str, where: str) -> None:
    try:
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(path=where)
    except (tarfile.TarError, IOError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Couldn't extract tarball: {exc}",
        )


async def get_call_info_by(uuid: UUID, url: str, key_id: str, key: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"uuid": str(uuid)},
        )
        logging.info(f"Get call INFO: {response.status_code=} {response.json()=}")
        response.raise_for_status()
        return response.json()


async def get_call_download_url(data: dict, url: str, key_id: str, key: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data=data,
        )
        logging.info(f"Get download URL: {response.status_code=} {response.json()=}")
        response.raise_for_status()
        return response.json()


def filter_calls(calls: list[dict]) -> list[dict]:
    return list(filter(lambda entry: entry["user_talk_time"] != 0, calls))


def paginate_response(
    array: list[t.Any], page_number: int, page_size: t.Optional[int] = 10
) -> list[t.Any]:
    return [
        array[index : index + page_size] for index in range(0, len(array), page_size)
    ][page_number]


def test_pbx_credentials(domain: str, key: str, key_id: str) -> bool:
    url = f"{settings.PBX_API_URL.format(domain=domain)}/user/get.json"

    try:
        response = requests.post(
            url,
            headers={
                "x-pbx-authentication": f"{key_id}:{key}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )

        if response.json()["status"] != "1":
            logging.error(
                f"Testing pbx credentials {domain=} {key=} {key_id=} failed: {response.json()=}"
            )
            return False

        return True

    except Exception as exc:
        logging.info(
            f"Testing pbx credentials {domain=} {key=} {key_id=} failed: {exc=}"
        )
        return False


def get_pbx_keys(
    domain: str, api_key: str
) -> tuple[t.Union[str, None], t.Union[str, None]]:
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

        response_content = response.json()
        if (
            response.status_code == status.HTTP_200_OK
            and response_content["status"] == "1"
        ):
            return response_content["data"]["key_id"], response_content["data"]["key"]

        return None, None

    except Exception as exc:
        logging.info(f"Could not get pbx keys: {exc=}")
        return None, None
