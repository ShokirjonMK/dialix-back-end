"""
SQL injection alert ...
We/You/I need to move ORM stuff asap. Otherwise there will be big mess.
Raw sql queries are not gonna work...

@Abduaziz
"""

import uuid
import logging
import typing as t

import psycopg2
import psycopg2.extras
from psycopg2.extensions import register_adapter, connection as Connection

from backend.services.record import get_records_sa
from backend.services.result import get_results_by_record_id_sa
from backend.database.utils import db_connection_wrapper, select_many, select_one

register_adapter(uuid.UUID, lambda _uuid: psycopg2.extensions.AsIs(str(uuid)))


@db_connection_wrapper
def get_user_by_email(connection: Connection, email: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute("SELECT * FROM account WHERE email = %s", (email,))
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_balance(connection: Connection, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "SELECT SUM(amount) as sum FROM transaction WHERE owner_id = %s",
            (owner_id,),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def upsert_record(connection: Connection, record):
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
def get_record_by_id(connection: Connection, record_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM record WHERE id = %s AND owner_id = %s",
        (record_id, owner_id),
    )


@db_connection_wrapper
def get_records_v1(
    connection: Connection, owner_id: str, filter_params: t.Optional[dict] = {}
):
    sql_query, query_params = get_records_sa(owner_id, **filter_params)
    return select_many(connection, sql_query, query_params)


@db_connection_wrapper
def get_records_v2(connection: Connection, owner_id: str):
    """Optimized version of get_records_v1 (line: 246)
    Uses postgres' JSON features, like selecting specefic key from `jsonb` payload.
    Difference: it will only select conversation_text from payload::json
    """
    return select_many(
        connection,
        "select "
        "id, owner_id, title, duration, operator_code, operator_name, "
        "call_type, source, status, storage_id, created_at, updated_at, "
        "deleted_at, payload#>'{result,conversation_text}' as conversation_text "
        "from record where owner_id = %s",
        (owner_id,),
    )


@db_connection_wrapper
def get_count_of_records(connection: Connection, owner_id: str):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        cursor.execute(
            "SELECT COUNT(*) FROM record WHERE owner_id = %s",
            (owner_id,),
        )
        return dict(cursor.fetchone())


@db_connection_wrapper
def get_pending_audios(connection: Connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM record WHERE owner_id = %s AND status = 'PENDING'",
        (owner_id,),
    )


@db_connection_wrapper
def upsert_checklist(connection: Connection, checklist: dict):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [key for key in checklist if key not in ["created_at", "updated_at"]]
        id = checklist["id"]

        cursor.execute(
            f"""
            INSERT INTO checklist ({', '.join(keys)}) 
            VALUES ({', '.join(['%s'] * len(keys))}) 
            ON CONFLICT (id) DO UPDATE 
            SET {', '.join([f'{key} = %s' for key in keys])}, 
                updated_at = NOW() 
            WHERE checklist.id = %s 
            RETURNING *
            """,
            tuple(
                [
                    psycopg2.extras.Json(checklist[key])
                    if key == "payload"
                    else checklist[key]
                    for key in keys
                ]
            )
            * 2
            + (id,),
        )

        return dict(cursor.fetchone())


@db_connection_wrapper
def update_checklist(connection: Connection, checklist_id: str, update_data: dict):
    with connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
        keys = [f"{key} = %s" for key in update_data]
        values = list(update_data.values())

        cursor.execute(
            f"""
            UPDATE checklist 
            SET {', '.join(keys)}, updated_at = NOW() 
            WHERE id = %s 
            RETURNING *
            """,
            values + [checklist_id],
        )

        updated_checklist = cursor.fetchone()
        return dict(updated_checklist) if updated_checklist else None


@db_connection_wrapper
def get_checklist_by_id(connection: Connection, checklist_id: str, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM checklist WHERE id = %s AND owner_id = %s",
        (checklist_id, owner_id),
    )


@db_connection_wrapper
def activate_checklist(connection: Connection, checklist_id: str, owner_id: str):
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
def get_active_checklist(connection: Connection, owner_id: str):
    return select_one(
        connection,
        "SELECT * FROM checklist WHERE owner_id = %s AND active = TRUE",
        (owner_id,),
    )


@db_connection_wrapper
def upsert_result(connection: Connection, result: dict):
    logging.info(f"Inserting result data: {result=}")

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
def get_result_by_record_id_v1(connection, record_id: str, owner_id: str):
    # without filter
    return select_one(
        connection,
        "SELECT * FROM result WHERE record_id = %s AND owner_id = %s",
        (record_id, owner_id),
    )


@db_connection_wrapper
def get_result_by_record_id(
    connection: Connection,
    record_id: str,
    owner_id: str,
    filter_params: t.Optional[dict] = {},
):
    sql_query, query_params = get_results_by_record_id_sa(
        record_id, owner_id, **filter_params
    )
    return select_one(connection, sql_query, query_params)


@db_connection_wrapper
def get_results(connection: Connection, owner_id: str):
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


@db_connection_wrapper
def create_transaction(connection: Connection, owner_id, record_id, amount, type):
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
    connection: Connection,
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
def upsert_operator(connection: Connection, operator: dict):
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
def get_operators(connection: Connection, owner_id: str):
    return select_many(
        connection,
        "SELECT * FROM operator_data WHERE owner_id = %s",
        (owner_id,),
    )


@db_connection_wrapper
def get_number_of_operators_records_count(
    connection: Connection, owner_id: str, operator_code: int
):
    query = "SELECT COUNT(*) FROM record WHERE owner_id = %s AND operator_code = %s"
    params = (owner_id, operator_code)
    return select_one(connection, query, params)


@db_connection_wrapper
def get_number_records(connection: Connection, owner_id: str):
    query = "SELECT COUNT(*) FROM record WHERE owner_id = %s"
    params = (owner_id,)
    return select_one(connection, query, params)


@db_connection_wrapper
def get_operator_name_by_code(connection: Connection, owner_id: str, code: int):
    return select_one(
        connection,
        "SELECT name FROM operator_data WHERE owner_id = %s AND code = %s",
        (owner_id, code),
    )
