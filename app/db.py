import datetime
import logging

import psycopg2
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from functools import wraps
from psycopg2.extras import DictCursor
from psycopg2.pool import ThreadedConnectionPool
from threading import Semaphore
from threading import Lock

DATABASE_URL = "postgresql://username:password@localhost/mydatabase"
pool: ThreadedConnectionPool = None
pool_lock = Lock()

def get_pool():
    global pool
    if pool is None:
        with pool_lock:
            if pool is None:
                pool = ThreadedConnectionPool(
                    minconn=1,
                    maxconn=10,
                    dsn="postgres://dev:dev@localhost:4655/studio"
                )
    return pool

class ConnectionWrapper:
    def __enter__(self):
        self.pool = get_pool()
        self.connection = self.pool.getconn()
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        self.pool.putconn(self.connection)

class ThreadedConnectionPool(ThreadedConnectionPool):
    def __init__(self, minconn, maxconn, *args, **kwargs):
        self._semaphore = Semaphore(maxconn)
        super().__init__(minconn, maxconn, *args, **kwargs)

    def putconn(self, *args, **kwargs):
        try:
            super().putconn(*args, **kwargs)
        finally:
            self._semaphore.release()

# Decorator to handle database connections
def db_connection_wrapper(func):
    def wrapper(*args, **kwargs):
        start_time = datetime.datetime.now()
        with ConnectionWrapper() as connection:
            exception = None
            try:
                return func(connection, *args, **kwargs)
            except Exception as e:
                exception = e
                raise e
            finally:
                if datetime.datetime.now() - start_time > datetime.timedelta(
                        seconds=0.5
                ):
                    logging.info(
                        f"Slow query: {func.__name__} took {datetime.datetime.now() - start_time}"
                    )
                if exception:
                    connection.rollback()
                else:
                    connection.commit()

    wrapper.__name__ = func.__name__
    return wrapper



# Database operation functions
@db_connection_wrapper
def execute(connection, query: str, values: dict = {}):
    return connection.execute(text(query), values)


@db_connection_wrapper
def select_one(connection, query: str, values: dict = {}):
    result = connection.execute(text(query), values)
    return result.fetchone()


@db_connection_wrapper
def select_many(connection, query: str, values: dict = {}):
    result = connection.execute(text(query), values)
    return result.fetchall()


# @db_connection_wrapper
# def create_user(username, hashed_password):
#         query = "INSERT INTO users (username, hashed_password) VALUES (:username, :hashed_password)"
#         conn.execute(query, {"username": username, "hashed_password": hashed_password})
#
#
# @db_connection_wrapper
# def get_user(user_id):
#         query = "SELECT * FROM users WHERE id = :user_id"
#         result = conn.execute(query, {"user_id": user_id})
#         return result.fetchone()

