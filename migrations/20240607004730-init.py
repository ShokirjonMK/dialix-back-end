import psycopg2
import psycopg2.extensions


def up(cursor: psycopg2.extensions.cursor):
    # account (id, email, password, space_limit, space_used, created_at, updated_at)
    cursor.execute(
        """
        CREATE TABLE account (
                id uuid PRIMARY KEY,
                email varchar NOT NULL UNIQUE,
                username varchar NOT NULL UNIQUE,
                password varchar NOT NULL,
                role varchar NOT NULL,
                company_name varchar NOT NULL,
                created_at timestamp NOT NULL default now(),
                updated_at timestamp NOT NULL default now()
            )
        """
    )

    # video (id, title, owner_id, youtube_url?, created_at, updated_at, deleted_at, language, audio_url)
    cursor.execute(
        """
        CREATE TABLE record (
                id uuid PRIMARY KEY,
                owner_id uuid NOT NULL,
                title varchar NOT NULL,
                duration bigint,
                payload jsonb,
                operator_code varchar,
                operator_name varchar,
                call_type varchar,
                source varchar,
                status varchar,
                storage_id varchar,
                created_at timestamp NOT NULL default now(),
                updated_at timestamp NOT NULL default now(),
                deleted_at timestamp,
                FOREIGN KEY (owner_id) REFERENCES account(id)
            )
        """
    )
    # transaction (id, owner_id, amount, created_at, updated_at, deleted_at)
    cursor.execute(
        """
        CREATE TABLE transaction (
                id uuid PRIMARY KEY,
                owner_id uuid NOT NULL,
                amount bigint NOT NULL,
                type varchar NOT NULL,
                record_id uuid,
                created_at timestamp NOT NULL default now(),
                updated_at timestamp NOT NULL default now(),
                FOREIGN KEY (owner_id) REFERENCES account(id),
                FOREIGN KEY (record_id) REFERENCES record(id)
            )
        """
    )
    # checklist (id, owner_id, title, payload, created_at, updated_at, deleted_at)
    cursor.execute(
        """
        CREATE TABLE checklist (
                id uuid PRIMARY KEY,
                owner_id uuid NOT NULL,
                title varchar NOT NULL,
                payload jsonb,
                active boolean NOT NULL default false,
                created_at timestamp NOT NULL default now(),
                updated_at timestamp NOT NULL default now(),
                deleted_at timestamp,
                FOREIGN KEY (owner_id) REFERENCES account(id)
            )
        """
    )
    # result (id, owner_id, record_id, checklist_id, operator_answer_delay, operator_speech_duration, customer_speech_duration, is_conversation_over, sentiment_analysis_of_conversation, sentiment_analysis_of_operator, sentiment_analysis_of_customer, is_customer_satisfied, is_customer_agreed_to_buy, is_customer_interested_to_product, summary, conversation, customer_gender, created_at, updated_at, deleted_at)
    cursor.execute(
        """
        CREATE TABLE result (
                id uuid PRIMARY KEY,
                owner_id uuid NOT NULL,
                record_id uuid NOT NULL,
                checklist_id uuid,
                operator_answer_delay bigint,
                operator_speech_duration bigint,
                customer_speech_duration bigint,
                is_conversation_over boolean,
                sentiment_analysis_of_conversation varchar,
                sentiment_analysis_of_operator varchar,
                sentiment_analysis_of_customer varchar,
                is_customer_satisfied boolean,
                is_customer_agreed_to_buy boolean,
                is_customer_interested_to_product boolean,
                which_course_customer_interested varchar,
                summary varchar,
                customer_gender varchar,
                checklist_result jsonb,
                created_at timestamp NOT NULL default now(),
                updated_at timestamp NOT NULL default now(),
                deleted_at timestamp,
                FOREIGN KEY (owner_id) REFERENCES account(id),
                FOREIGN KEY (record_id) REFERENCES record(id),
                FOREIGN KEY (checklist_id) REFERENCES checklist(id)
            )
        """
    )
