import logging
import datetime

from decouple import config

import psycopg2
import psycopg2.extras
from psycopg2.pool import SimpleConnectionPool


pool: SimpleConnectionPool | None = None


def get_pool() -> SimpleConnectionPool:
    global pool

    if pool is None:
        pool = SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=config("DATABASE_URL"),
        )

    return pool


class ConnectionWrapper:
    def __enter__(self):
        self.pool = get_pool()
        self.current_connection = self.pool.getconn()
        return self.current_connection

    def __exit__(self, exc_type, exc_value, traceback):
        self.pool.putconn(self.current_connection)


def db_connection_wrapper(func):
    def wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()

        with ConnectionWrapper() as connection:
            exception = None
            
            try:
                return func(connection, *args, **kwargs)
            except Exception as exc:
                exception = exc
                raise exc
            finally:
                if datetime.datetime.now() - start_time > datetime.timedelta(
                    seconds=0.5
                ):
                    logging.warning(
                        f"Slow query: {func.__name__} took {datetime.datetime.now() - start_time}"
                    )
                if exception:
                    connection.rollback()
                else:
                    connection.commit()

    wrapper.__name__ = func.__name__
    return wrapper


def select_one(connection, query, params=None) -> dict | None:
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(query, params)
        result = cursor.fetchone()
        return dict(result) if result else None


def select_many(connection, query, params=None) -> list[dict] | list:
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [dict(result) for result in results] if results else []
