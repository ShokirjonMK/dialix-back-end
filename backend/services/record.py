import typing as t
from uuid import UUID

from sqlalchemy import select
# from sqlalchemy.orm import Session

from backend.database.models import Record
from backend.database.utils import compile_sql_query_and_params


def get_records_sa(  # sa -> SQLAlchemy
    owner_id: UUID,
    operator_code: t.Optional[str] = None,
    operator_name: t.Optional[str] = None,
    call_type: t.Optional[str] = None,
    call_status: t.Optional[str] = None,
    client_phone_number: t.Optional[str] = None,
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

    return compile_sql_query_and_params(statement)
