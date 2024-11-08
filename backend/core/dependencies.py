from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from backend.database.session_manager import get_db_session

DatabaseSessionDependency = Annotated[Session, Depends(get_db_session)]
