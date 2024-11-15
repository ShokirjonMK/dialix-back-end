import logging
from sqlalchemy import text

from backend.database.session_manager import get_db_session


def is_db_working() -> bool | None:
    db_session = next(get_db_session())

    is_working: bool = False

    try:
        db_version = db_session.execute(text("select version();")).scalar()
        logging.info(f"{db_version=}")
        is_working = True
    except Exception as exc:
        logging.error(f"Can't connect to database: {exc=} {db_version=}")
    finally:
        return is_working
