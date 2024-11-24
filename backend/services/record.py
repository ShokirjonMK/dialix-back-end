import typing as t
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database.models import Record
from backend.utils.shortcuts import get_filterable_values_for
from backend.database.utils import compile_sql_query_and_params


def get_record_by_title(db_session: Session, owner_id: UUID, title: str) -> Record:
    statement = select(Record).where(
        (Record.owner_id == owner_id) & (Record.title.contains(title))
    )
    return db_session.scalar(statement)


def get_all_record_titles(db_session: Session, owner_id: UUID):
    statement = select(Record.title).where((Record.owner_id == owner_id))
    return db_session.scalars(statement).all()


def get_filterable_values_for_record(
    db_session: Session, owner_id: UUID
) -> dict[str, list[str]]:
    return get_filterable_values_for(
        Record,
        [
            "call_type",
            "client_phone_number",
            "operator_code",
            "operator_name",
            "status",
            "duration",
        ],
        db_session,
        owner_id,
    )


def get_records_sa(  # sa -> SQLAlchemy
    owner_id: UUID,
    operator_code: t.Optional[str] = None,
    operator_name: t.Optional[str] = None,
    call_type: t.Optional[str] = None,
    call_status: t.Optional[str] = None,
    client_phone_number: t.Optional[str] = None,
    transcript_contains: t.Optional[str] = None,
):
    statement = select(Record).where(Record.owner_id == owner_id)

    if operator_code:
        statement = statement.where(Record.operator_code == operator_code)

    if operator_name:
        statement = statement.where(Record.operator_name.ilike(operator_name))

    if call_type:
        statement = statement.where(Record.call_type == call_type)

    if call_status:
        statement = statement.where(Record.status == call_status)

    if client_phone_number:
        statement = statement.where(
            Record.client_phone_number.contains(client_phone_number)
        )

    if transcript_contains:
        statement = statement.where(
            Record.payload["result"].op("->>")("text").contains(transcript_contains)
        )

    return compile_sql_query_and_params(statement)
