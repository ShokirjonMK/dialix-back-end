import logging
import contextlib
import typing as t

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from backend.core import settings


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, t.Any] = {}):
        self._engine = create_engine(host, **engine_kwargs)
        self._sessionmaker = sessionmaker(autocommit=False, bind=self._engine)

    def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.contextmanager
    def connect(self) -> t.Iterator[Connection]:
        if self._engine is None:
            raise Exception("DB session manager is not initialized")

        with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                connection.rollback()
                raise

    @contextlib.contextmanager
    def session(self) -> t.Iterator[Session]:
        if self._sessionmaker is None:
            raise Exception("DB session manager is not initialized")

        session = self._sessionmaker()

        try:
            yield session
        except Exception as exc:
            logging.info(f"Rolling back: {exc=}")
            session.rollback()
            raise
        finally:
            session.close()


sessionmanager = DatabaseSessionManager(
    settings.DATABASE_URL, {"echo": settings.ECHO_SQL}
)
