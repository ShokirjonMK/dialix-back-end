import logging
import contextlib
import typing as t

from sqlalchemy import create_engine
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Session, sessionmaker

from backend.core import settings


class DatabaseSessionManager:
    def __init__(self, host: str, engine_kwargs: dict[str, t.Any] = {}):
        # Optimized connection pooling
        optimized_kwargs = {
            "pool_size": 10,  # Connection pool size
            "max_overflow": 20,  # Max connections beyond pool_size
            "pool_pre_ping": True,  # Verify connections before use
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "echo": engine_kwargs.get("echo", False),
        }
        optimized_kwargs.update(engine_kwargs)

        self._engine = create_engine(host, **optimized_kwargs)
        self._sessionmaker = sessionmaker(
            autocommit=False,
            autoflush=False,  # Optimize performance
            bind=self._engine,
            expire_on_commit=False,  # Cache model objects
        )

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
            # logging.info(f"Rolling back: {exc=}")
            session.rollback()
            raise
        finally:
            session.close()


sessionmanager = DatabaseSessionManager(
    settings.DATABASE_URL, {"echo": settings.ECHO_SQL}
)
