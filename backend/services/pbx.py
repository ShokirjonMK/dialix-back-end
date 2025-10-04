import logging  # noqa: F401
from uuid import UUID

from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

from backend.database.models import PbxCall


def sync_pbx_calls(
    db_session: Session, owner_id: UUID, pbx_calls: list[dict]
) -> list[PbxCall]:
    if pbx_calls is None:
        return []
    call_objects = [
        PbxCall(
            owner_id=owner_id,
            call_id=call_data["uuid"],
            caller_id_name=call_data["caller_id_name"],
            caller_id_number=call_data["caller_id_number"],
            destination_number=call_data["destination_number"],
            start_stamp=call_data["start_stamp"],
            end_stamp=call_data["end_stamp"],
            duration=call_data["duration"],
            user_talk_time=call_data["user_talk_time"],
            call_type=call_data["accountcode"],
        )
        for call_data in pbx_calls
    ]
    db_session.add_all(call_objects)
    db_session.commit()

    return pbx_calls


def get_total_interval(db_session: Session, owner_id: UUID) -> tuple[int, int]:
    return db_session.execute(
        select(
            func.min(PbxCall.start_stamp).label("min_start"),
            func.max(PbxCall.end_stamp).label("max_end"),
        ).where(PbxCall.owner_id == owner_id)
    ).first()


def get_calls_between_interval(
    db_session: Session, owner_id: UUID, S: int, E: int
) -> list[tuple[int, int]]:
    return (
        db_session.query(PbxCall)
        .filter(
            PbxCall.owner_id == owner_id,
            PbxCall.start_stamp >= S,
            PbxCall.end_stamp <= E,
        )
        .all()
    )


def get_no_bitrix_processed_calls(db_session: Session, owner_id: UUID):
    return (
        db_session.query(PbxCall.destination_number.distinct())
        .filter(
            PbxCall.bitrix_result.is_(None),
            PbxCall.owner_id == owner_id,
            PbxCall.was_processed_from_bitrix == False,  # noqa: E712
        )
        .all()
    )


def update_bitrix_results_by_phone_number(
    db_session: Session, owner_id: UUID, phone_number: str, result: dict
) -> None:
    query = (
        update(PbxCall)
        .filter(
            PbxCall.owner_id == owner_id,
            PbxCall.destination_number == phone_number,
        )
        .values(bitrix_result=result, was_processed_from_bitrix=True)
    )

    db_session.execute(query)
    db_session.commit()


def get_bitrix_result_by_call_id(
    db_session: Session, owner_id: UUID, call_id: UUID
) -> dict:
    query = select(PbxCall.bitrix_result).where(
        PbxCall.owner_id == owner_id, PbxCall.call_id == call_id
    )
    return db_session.execute(query).scalar()
