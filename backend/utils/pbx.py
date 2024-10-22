import os
import logging
import tarfile
import requests
import typing as t
from uuid import UUID

from fastapi import HTTPException, status


def download_from(url: str, save_where: str) -> str:
    try:
        os.makedirs(os.path.dirname(save_where), exist_ok=True)

        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(save_where, "wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        return save_where
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Couldn't download tarball: {exc}",
        )


def extract_tar_file(tar_path: str, where: str) -> None:
    try:
        with tarfile.open(tar_path, "r") as tar:
            tar.extractall(path=where)
    except (tarfile.TarError, IOError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Couldn't extract tarball: {exc}",
        )


def get_call_info_by(uuid: UUID, url: str, key_id: str, key: str) -> dict:
    response = requests.post(
        url,
        headers={
            "x-pbx-authentication": f"{key_id}:{key}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={"uuid": uuid},
    )
    logging.info(f"Get call INFO: {response.status_code=} {response.json()=}")
    response.raise_for_status()
    return response.json()


def get_call_download_url(data: dict, url: str, key_id: str, key: str) -> dict:
    response = requests.post(
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


def paginate_response(
    array: list[t.Any], page_number: int, page_size: t.Optional[int] = 10
) -> list[t.Any]:
    return [
        array[index : index + page_size] for index in range(0, len(array), page_size)
    ][page_number]
