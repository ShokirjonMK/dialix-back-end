import datetime
import logging
import os
import re

from fastapi import HTTPException
from filelock import FileLock
from google.cloud import storage
from utils.redis_utils import cache

storage_client: storage.Client() = None


def get_client():
    global storage_client
    if storage_client is None:
        storage_client = storage.Client()
    return storage_client


def folder_exists(bucket_name: str, folder_name: str) -> bool:
    client = get_client()
    bucket = client.bucket(bucket_name)
    blobs = list(bucket.list_blobs(prefix=folder_name))
    return any(blob.name == f"{folder_name}/" for blob in blobs)


def download_file(bucket, remote_path, local_path):
    if os.path.isdir(local_path):
        local_path = os.path.join(local_path, os.path.basename(remote_path))
    else:
        local_path = local_path

    lock_file_path = f"{local_path.rstrip('/')}.lock"
    lock = FileLock(lock_file_path)
    with lock:
        if os.path.exists(local_path):
            # print("File ", local_path, "already exists. Skipping...")
            return local_path
        # if local_path is folder
        client = get_client()
        bucket = client.get_bucket(bucket)
        blob: storage.blob.Blob = bucket.blob(remote_path)
        blob.download_to_filename(local_path)
        return local_path


def exists(bucket, remote_path):
    client = get_client()
    bucket = client.get_bucket(bucket)
    blob: storage.blob.Blob = bucket.blob(remote_path)
    return blob.exists()


def file_exists(file_id):
    client = get_client()
    bucket = client.get_bucket(os.getenv("STORAGE_BUCKET_NAME", "dialixai-production"))
    blob: storage.blob.Blob = bucket.blob(file_id)
    return blob.exists()


def upload_file(bucket, remote_path, local_path):
    client = get_client()
    bucket = client.get_bucket(bucket)
    blob: storage.blob.Blob = bucket.blob(remote_path)
    # if is folder
    if remote_path[-1] == "/":
        local_path = os.path.join(
            local_path,
            os.path.basename(remote_path),
        )

    blob.upload_from_filename(local_path)
    return local_path


def delete_file(file_id):
    client = get_client()
    bucket = client.get_bucket(os.getenv("STORAGE_BUCKET_NAME", "dialixai-production"))
    blob: storage.blob.Blob = bucket.blob(file_id)
    blob.delete()


def _get_stream_url(
    file_id, bucket=os.getenv("STORAGE_BUCKET_NAME", "dialixai-production")
):
    client = get_client()
    bucket = client.get_bucket(bucket)
    blob: storage.blob.Blob = bucket.blob(file_id)
    url = blob.generate_signed_url(
        expiration=datetime.timedelta(hours=24),
        method="GET",
        virtual_hosted_style=True,
        version="v4",
    )
    return url


get_stream_url = cache.cache(
    ttl=60 * 60 * 24, limit=0, namespace=os.getenv("STORAGE_REDIS_KEY", "storage")
)(_get_stream_url)


def get_upload_url(file_id, content_type="video/mp4"):
    client = get_client()
    bucket = client.get_bucket(os.getenv("STORAGE_BUCKET_NAME", "dialixai-production"))
    blob: storage.blob.Blob = bucket.blob(file_id)
    url = blob.generate_signed_url(
        expiration=datetime.timedelta(minutes=60 * 24),
        # content_type=content_type,
        method="PUT",
        virtual_hosted_style=True,
        version="v4",
    )
    return url


def parse_signed_url(signed_url):
    # example signed_upload_url = https://staging-studio.storage.googleapis.com/0ea6b848-8e58-487a-a988-83c455dc7080.audio?X-Goog-Algorithm=GOOG4-RSA-SHA256&X-Goog-Credential=studio-cluster-manager-117%40mohirdev-379005.iam.gserviceaccount.com%2F20230824%2Fauto%2Fstorage%2Fgoog4_request&X-Goog-Date=20230824T074528Z&X-Goog-Expires=345600&X-Goog-SignedHeaders=host&X-Goog-Signature=830b88bfd889f212d620995e71b796a1d11ce232e906fd72639a5405f4d8b83a019b5980406c5402e614ac2d68d121bf5a84931aaf689c93b2aa0bf0e589a9ec06daa944bfcc99714be640c8c5950201c046f01941e6cba0bd43d4552c72b355f9a614d9c4cf5c7237eb1929b8c3aca758684b9d28a24f8dcd357c83c0f21cae4ab4e7b62ccd92b38bf2d4c72f7686e72768f21e7d92c91f7e18173f39d1178fde0e956d8bb2c5bfe96abcb55d3fd6314183f4a302d20c023f415401f8f6fe72efe7f3c2ce44ee235405b9d7a4755ddf1058967f0d96d82c37eff0c8453aac8f6d25ad51d3865804c406cfd387cf17e2cf755d2add9a9a68274f3916edeee6a7
    bucket = re.findall(r"https://(.+?).storage.googleapis.com", signed_url)[0]
    file_id = re.findall(r"storage.googleapis.com/(.+?)\?", signed_url)[0]
    return bucket, file_id
