import psycopg2
import psycopg2.extensions


def up(cursor: psycopg2.extensions.cursor):
    # account (id, email, password, space_limit, space_used, created_at, updated_at)
    cursor.execute(
        """
            ALTER TABLE record
            ADD COLUMN status varchar(20);
        """
    )
