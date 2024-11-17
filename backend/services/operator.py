import logging  # noqa: F401
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.database.models import OperatorData


def get_operator(
    db_session: Session, owner_id: UUID, operator_id: UUID
) -> OperatorData:
    return db_session.scalar(
        select(OperatorData).where(
            (OperatorData.owner_id == owner_id) & (OperatorData.id == operator_id)
        )
    )


def get_operators(
    db_session: Session,
    owner_id: UUID,
) -> list[OperatorData]:
    return db_session.scalars(
        select(OperatorData)
        .where(OperatorData.owner_id == owner_id)
        .order_by(OperatorData.code)
    ).all()


def create_operator(
    db_session: Session, owner_id: UUID, operator_data: dict
) -> OperatorData:
    operator_data["owner_id"] = owner_id
    operator = OperatorData(**operator_data)

    db_session.add(operator)
    db_session.commit()

    return operator


def create_operators(
    db_session: Session, operators_data: list[dict]
) -> list[OperatorData]:
    operators = [OperatorData(**operator_data) for operator_data in operators_data]

    db_session.add_all(operators)
    db_session.commit()

    return operators


def delete_operator(db_session: Session, owner_id: UUID, operator_id: UUID) -> bool:
    if not (operator := get_operator(db_session, owner_id, operator_id)):
        return False

    db_session.delete(operator)
    db_session.commit()

    return True


def update_operator(
    db_session: Session, owner_id: UUID, operator_id: UUID, update_values: dict
) -> bool:
    if not get_operator(db_session, owner_id, operator_id):
        return False

    update_query = (
        update(OperatorData)
        .where((OperatorData.id == operator_id) & (OperatorData.owner_id == owner_id))
        .values(**update_values)
    )

    db_session.execute(update_query)
    db_session.commit()

    return True
