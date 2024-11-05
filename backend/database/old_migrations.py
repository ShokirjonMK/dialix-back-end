"""Migration utility"""

import os
import datetime
import warnings

import psycopg2
import psycopg2.extras

from backend.database.utils import ConnectionWrapper


def migrate_up():
    warnings.warn(
        "Please, do not use this function, if it is possible. "
        "Use another migration tools like aerich/alembic, which suits to your ORM."
        "Any questions: tg/@AbduazizZiyodov"
    )

    with ConnectionWrapper() as connection:
        os.makedirs("./old_migrations", exist_ok=True)
        existing_migrations = []
        cursor = connection.cursor(cursor_factory=psycopg2.extras.DictCursor)

        try:
            cursor.execute("SELECT * FROM migrations")
            existing_migrations = cursor.fetchall()
            connection.commit()
        except Exception as exc:
            connection.rollback()
            print(f'Creating "migrations" table... {exc=}')
            cursor.execute(
                "CREATE TABLE migrations (id varchar PRIMARY KEY, created_at timestamp NOT NULL)"
            )
            pass

        migration_files = os.listdir("./old_migrations")
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
