import logging  # noqa: F401
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import OperatorData


def get_operators(
    db_session: Session,
    owner_id: UUID,
) -> list[OperatorData]:
    return db_session.scalars(
        select(OperatorData).where(OperatorData.owner_id == owner_id)
    )


def create_operators(
    db_session: Session, operators_data: list[dict]
) -> list[OperatorData]:
    operators = [OperatorData(**operator_data) for operator_data in operators_data]

    db_session.add_all(operators)
    db_session.commit()

    return operators
