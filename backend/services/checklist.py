import logging  # noqa: F401
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.database.models import Checklist
from backend.utils.shortcuts import raise_400


def get_checklists_by_owner_id(db_session: Session, owner_id: UUID) -> list[Checklist]:
    return db_session.scalars(
        select(Checklist).where(Checklist.owner_id == owner_id)
    ).all()


def get_single_checklist(
    db_session: Session,
    owner_id: UUID,
    checklist_id: UUID,
) -> list[Checklist]:
    return db_session.scalar(
        select(Checklist).where(
            Checklist.id == checklist_id, Checklist.owner_id == owner_id
        )
    )


def insert_checklist(db_session: Session, checklist_data: dict) -> None:
    new_checklist = Checklist(**checklist_data)
    db_session.add(new_checklist)

    try:
        db_session.commit()
        return new_checklist
    except IntegrityError:
        db_session.rollback()
        return raise_400("Checklist with this ID already exists.")
