import logging  # noqa: F401
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import Checklist


def get_checklists_by_owner_id(db_session: Session, owner_id: UUID) -> list[Checklist]:
    return db_session.scalars(
        select(Checklist).where(Checklist.owner_id == owner_id)
    ).all()


def get_single_checklist(
    db_session: Session, owner_id: UUID, checklist_id: UUID
) -> list[Checklist]:
    return db_session.scalar(
        select(Checklist).where(
            Checklist.id == checklist_id, Checklist.owner_id == owner_id
        )
    )


def create_checklist(db_session: Session, owner_id: UUID, checklist_data: dict) -> None:
    checklist_data["owner_id"] = owner_id
    new_checklist = Checklist(**checklist_data)
    db_session.add(new_checklist)
    db_session.commit()

    return new_checklist


def delete_checklist(db_session: Session, owner_id: UUID, checklist_id: UUID) -> bool:
    if not (checklist := get_single_checklist(db_session, owner_id, checklist_id)):
        return False

    db_session.delete(checklist)
    db_session.commit()

    return True
