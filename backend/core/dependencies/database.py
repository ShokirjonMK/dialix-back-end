import typing as t

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.database.session_manager import sessionmanager


def get_db_session() -> t.Generator[Session, t.Any, None]:
    with sessionmanager.session() as session:
        yield session


DatabaseSessionDependency = t.Annotated[Session, Depends(get_db_session)]
