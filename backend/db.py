import datetime
import logging
import os
import uuid
import psycopg2
from decouple import config
from psycopg2.extensions import register_adapter
from psycopg2.pool import SimpleConnectionPool

pool: SimpleConnectionPool = None


def adapt_uuid(uuid):
    return psycopg2.extensions.AsIs(str(uuid))


register_adapter(uuid.UUID, adapt_uuid)


def get_pool():
    global pool
    if pool is None:
        dsn = config("DATABASE_URL")
        pool = SimpleConnectionPool(minconn=1, maxconn=10, dsn=dsn)
    return pool


class ConnectionWrapper:
    def __enter__(self):
        self.pool = get_pool()
        self.connection = self.pool.getconn()
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        self.pool.putconn(self.connection)


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


def migrate_up():
    with ConnectionWrapper() as connection:
        import os

        os.makedirs("./migrations", exist_ok=True)
        existing_migrations = []
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            cursor.execute("SELECT * FROM migrations")
            existing_migrations = cursor.fetchall()
            connection.commit()
        except:
            connection.rollback()
            print('Creating "migrations" table...')
            cursor.execute(
                "CREATE TABLE migrations (id varchar PRIMARY KEY, created_at timestamp NOT NULL)"
            )
            pass

        migration_files = os.listdir("./migrations")
        migration_files = [
            file
            for file in migration_files
            if file.endswith(".py") and "__pycach" not in file
        ]
        existing_migration_ids = set(
            [migration["id"] for migration in existing_migrations]
        )
        migration_files = [
            file for file in migration_files if file not in existing_migration_ids
        ]
        migration_files.sort()
        print(
            f"Found {len(migration_files)} migration files, running..."
            if len(migration_files) > 0
            else "No migration files found, skipping..."
        )
        for migration_file in migration_files:
            try:
                print(f"Running migration {migration_file}")
                # import migration file
                migration = __import__(
                    f"migrations.{migration_file[:-3]}", fromlist=["up"]
                )

                # run migration
                migration.up(cursor)
                query = "INSERT INTO migrations (id, created_at) VALUES (%s, %s)"
                cursor.execute(
                    query,
                    (
                        migration_file,
                        datetime.datetime.now(),
                    ),
                )
                connection.commit()
            except Exception as e:
                print(f"Error running migration {migration_file}: {e}")
                print("Stacktrace:")
                import traceback

                traceback.print_exc()
                exit(1)


def select_one(connection, query, params=None) -> dict:
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(query, params)
        result = cursor.fetchone()
        return dict(result) if result else None


def select_many(connection, query, params=None):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(query, params)
        results = cursor.fetchall()
        return [dict(result) for result in results] if results else []


def execute(connection, query, params=None):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(query, params)


@db_connection_wrapper
def create_user(connection, user_data: dict):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            """
            INSERT INTO account (id, email, username, password, role, company_name, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            RETURNING id;
            """,
            (
                str(user_data["id"]),
                user_data["email"],
                user_data["username"],
                user_data["password"],
                user_data["role"],
                user_data["company_name"],
            ),
        )
        user_id = cursor.fetchone()[0]
        connection.commit()
        return {**user_data, "id": user_id}


@db_connection_wrapper
def get_user_by_id(connection, user_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("SELECT * FROM account WHERE id = %s", (user_id,))
        return cursor.fetchone()


@db_connection_wrapper
def get_user_by_email(connection, email: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("SELECT * FROM account WHERE email = %s", (email,))
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_balance(connection, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "SELECT SUM(amount) FROM transaction WHERE owner_id = %s", (owner_id,)
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def upsert_record(connection, record):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [key for key in record.keys() if key not in ["created_at", "updated_at"]]
        id = record.get("id")

        cursor.execute(
            f"INSERT INTO record ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))}) ON CONFLICT (id) DO UPDATE SET {', '.join([f'{key} = %s' for key in keys])}, updated_at = NOW() WHERE record.id = %s RETURNING *",
            tuple(
                [
                    (
                        psycopg2.extras.Json(record[key])
                        if key == "payload" and isinstance(record[key], dict)
                        else record[key]
                    )
                    for key in keys
                ]
            )
            * 2
            + (id,),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_record_by_id(connection, record_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM record WHERE id = %s AND owner_id = %s",
        (record_id, owner_id),
    )


@db_connection_wrapper
def remove_record(connection, record_id: str, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "DELETE FROM record WHERE id = %s AND owner_id = %s",
            (record_id, owner_id),
        )
        deleted_record = dict(cursor.fetchone())
        if deleted_record:
            return deleted_record
        else:
            return None


@db_connection_wrapper
def get_records(connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM record WHERE owner_id = %s",
        (owner_id,),
    )


@db_connection_wrapper
def get_count_of_records(connection, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM record WHERE owner_id = %s",
            (owner_id,),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_pending_audios(connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM record WHERE owner_id = %s AND status = 'PENDING'",
        (owner_id,),
    )


@db_connection_wrapper
def get_count_of_records(connection, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM record WHERE owner_id = %s",
            (owner_id,),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def upsert_checklist(connection, checklist: dict):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [
            key for key in checklist.keys() if key not in ["created_at", "updated_at"]
        ]
        id = checklist["id"]

        cursor.execute(
            f"INSERT INTO checklist ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))}) ON CONFLICT (id) DO UPDATE SET {', '.join([f'{key} = %s' for key in keys])}, updated_at = NOW() WHERE checklist.id = %s RETURNING *",
            tuple(
                [
                    (
                        psycopg2.extras.Json(checklist[key])
                        if key == "payload" and isinstance(checklist[key], dict)
                        else checklist[key]
                    )
                    for key in keys
                ]
            )
            * 2
            + (id,),
        )

        return dict(cursor.fetchone())


@db_connection_wrapper
def get_checklists(connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM checklist WHERE owner_id = %s",
        (owner_id,),
    )


@db_connection_wrapper
def get_checklist_by_id(connection, checklist_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM checklist WHERE id = %s AND owner_id = %s",
        (checklist_id, owner_id),
    )


@db_connection_wrapper
def activate_checklist(connection, checklist_id: str, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "UPDATE checklist SET active = FALSE WHERE owner_id = %s",
            (owner_id,),
        )

        cursor.execute(
            "UPDATE checklist SET active = TRUE WHERE id = %s AND owner_id = %s RETURNING *",
            (checklist_id, owner_id),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_active_checklist(connection, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM checklist WHERE owner_id = %s AND active = TRUE",
        (owner_id,),
    )


@db_connection_wrapper
def delete_checklist(connection, checklist_id: str, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "DELETE FROM checklist WHERE id = %s AND owner_id = %s RETURNING *",
            (checklist_id, owner_id),
        )
        deleted_checklist = cursor.fetchone()
        if deleted_checklist:
            return deleted_checklist
        else:
            return None


@db_connection_wrapper
def upsert_result(
    connection,
    result: dict,
):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [key for key in result.keys() if key not in ["created_at", "updated_at"]]
        id = result["id"]

        cursor.execute(
            f"INSERT INTO result ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))}) ON CONFLICT (id) DO UPDATE SET {', '.join([f'{key} = %s' for key in keys])}, updated_at = NOW() WHERE result.id = %s RETURNING *",
            tuple(
                [
                    (
                        psycopg2.extras.Json(result[key])
                        if key == "checklist_result" and isinstance(result[key], dict)
                        else result[key]
                    )
                    for key in keys
                ]
            )
            * 2
            + (id,),
        )

        return dict(cursor.fetchone())


@db_connection_wrapper
def get_result_by_id(connection, result_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM result WHERE id = %s AND owner_id = %s",
        (result_id, owner_id),
    )


@db_connection_wrapper
def get_result_by_record_id(connection, record_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM result WHERE record_id = %s AND owner_id = %s",
        (record_id, owner_id),
    )


@db_connection_wrapper
def remove_result(connection, result_id: str, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "DELETE FROM result WHERE id = %s AND owner_id = %s RETURNING *",
            (result_id, owner_id),
        )
        deleted_result = cursor.fetchone()
        if deleted_result:
            return deleted_result
        else:
            return None


@db_connection_wrapper
def get_results(connection, owner_id: str):
    return select_many(
        connection,
        """
        SELECT r.id as result_id,
        r.operator_answer_delay,
        r.operator_speech_duration,
        r.customer_speech_duration,
        r.is_conversation_over,
        r.sentiment_analysis_of_conversation,
        r.sentiment_analysis_of_operator,
        r.sentiment_analysis_of_customer,
        r.is_customer_satisfied,
        r.is_customer_agreed_to_buy,
        r.is_customer_interested_to_product,
        r.summary,
        r.customer_gender,
        r.created_at as result_created_at,
        r.updated_at as result_updated_at,
        r.deleted_at as result_deleted_at,
        r.checklist_result,
        rec.id as record_id,
        rec.title as record_title,
        rec.duration as record_duration,
        rec.payload as record_payload,
        rec.operator_code as record_operator_code,
        rec.operator_name as record_operator_name,
        rec.call_type as record_call_type,
        rec.source as record_source,
        rec.status as record_status,
        rec.storage_id as record_storage_id,
        cl.id as checklist_id,
        cl.title as checklist_title,
        cl.payload as checklist_payload
        FROM result r
        LEFT JOIN record rec ON r.record_id = rec.id
        LEFT JOIN checklist cl ON r.checklist_id = cl.id
        WHERE r.owner_id = %s
        """,
        (owner_id,),
    )


MOHIRAI_PRICE_PER_MS = 630 / 60 / 1000 * 100
GENERAL_PROMPT_PRICE_PER_MS = 210 / 60 / 1000 * 100
CHECKLIST_PROMPT_PRICE_PER_MS = 360 / 60 / 1000 * 100


@db_connection_wrapper
def create_transaction(
    connection,
    owner_id,
    record_id,
    amount,
    type,
):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            """
            INSERT INTO transaction (id, owner_id, record_id, amount, type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING *;
            """,
            (
                str(uuid.uuid4()),
                owner_id,
                record_id,
                -amount,
                type,
            ),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def create_topup_transaction(
    connection,
    owner_id,
    amount,
    type,
):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            """
            INSERT INTO transaction (id, owner_id, amount, type)
            VALUES (%s, %s, %s, %s)
            RETURNING *;
            """,
            (
                str(uuid.uuid4()),
                owner_id,
                amount,
                type,
            ),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def upsert_operator(connection, operator: dict):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [
            key for key in operator.keys() if key not in ["created_at", "updated_at"]
        ]
        id = operator["id"]

        cursor.execute(
            f"INSERT INTO operator_data ({', '.join(keys)}) VALUES ({', '.join(['%s'] * len(keys))}) ON CONFLICT (id) DO UPDATE SET {', '.join([f'{key} = %s' for key in keys])}, updated_at = NOW() WHERE operator_data.id = %s RETURNING *",
            tuple([operator[key] for key in keys]) * 2 + (id,),
        )

        return dict(cursor.fetchone())


@db_connection_wrapper
def get_operators(connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM operator_data WHERE owner_id = %s",
        (owner_id,),
    )


@db_connection_wrapper
def get_number_of_operators_records_count(
    connection, owner_id: str, operator_code: int
):
    query = "SELECT COUNT(*) FROM record WHERE owner_id = %s AND operator_code = %s"
    params = (owner_id, operator_code)
    return select_one(connection, query, params)


@db_connection_wrapper
def get_number_records(connection, owner_id: str):
    query = "SELECT COUNT(*) FROM record WHERE owner_id = %s"
    params = (owner_id,)
    return select_one(connection, query, params)


@db_connection_wrapper
def get_operator_name_by_code(connection, owner_id: str, code: int):
    return select_one(
        connection,
        "SELECT name FROM operator_data WHERE owner_id = %s AND code = %s",
        (owner_id, code),
    )
