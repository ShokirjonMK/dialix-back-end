import os
import uuid
import shutil
import logging

from fastapi.responses import JSONResponse
from fastapi import Request, HTTPException, status


from backend import db
from backend.core import settings
from utils.audio import get_audio_duration
from backend.core.dependencies.user import get_current_user
from backend.core.dependencies.database import DatabaseSessionDependency


def get_object_storage_id(extension):
    return f"{uuid.uuid4()}.{extension}"


async def process_form_data(request: Request, db_session: DatabaseSessionDependency):
    form_data = await request.form()
    current_user = get_current_user(request, db_session)

    files = form_data.getlist("files")
    logging.info(f"{files=}")
    general = [gen == "true" for gen in form_data.getlist("general")]
    checklist_id = [
        checklist if checklist != "null" or checklist != "" else None
        for checklist in form_data.getlist("checklist_id")
    ]
    balance = db.get_balance(owner_id=str(current_user.id)).get("sum", 0) or 0
    balance = balance if balance is not None else 0
    total_price = 0
    processed_files = []

    for file, gen, checklist in zip(files, general, checklist_id):
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

        processed_files.append({"file_path": file_path, "duration": duration})

        mohirai_price = (
            duration * settings.MOHIRAI_PRICE_PER_MS
            if gen is True or checklist is not None
            else 0
        )
        general_price = (
            duration * settings.GENERAL_PROMPT_PRICE_PER_MS if gen is True else 0
        )
        checklist_price = (
            duration * settings.CHECKLIST_PROMPT_PRICE_PER_MS if checklist is not None else 0
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
