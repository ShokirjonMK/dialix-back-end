import psycopg2
import psycopg2.extensions


def up(cursor: psycopg2.extensions.cursor):
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS operator_data (
            id uuid PRIMARY KEY,
            owner_id uuid NOT NULL,
            code integer NOT NULL,
            name varchar NOT NULL,
            created_at timestamp NOT NULL default now(),
            updated_at timestamp NOT NULL default now(),
            deleted_at timestamp,
            FOREIGN KEY (owner_id) REFERENCES account(id)
        )
        """
    )