import json
import logging
import os

import openai

from utils.storage import download_file, file_exists
from workers.common import celery, PredictTask
from utils.data_manipulation import (
    convert_to_chat,
    process_transcription,
    find_position_from_filename,
    calculate_pause_duration,
    calculate_speech_duration,
    extract_json_from_markdown,
    convert_string_to_json,
)
import backend.db as db
from utils.mohirai import mohirAI

checklist_prompt = """
    You are given a conversation between a call center operator and a potential customer. The operator should ask certain questions from the list below. 
    Your task is to identify if questions are asked or not. If a question is asked then you should return  "question content": true, if not asked "question content": false

    Response format: 
    {
    "Question Content 1": true or false # true if asked, false if not asked,
    "Question Content 2": true or false # true if asked, false if not asked,
    ...
    }

    Here is the list of questions:
"""

courses_list = [
    "Kiberxavfsizlik: Pentesting",
    "Computer Vision",
    "Data Science va Sun'iy Intellekt",
    "Sunʼiy intellekt - NLP (nutq bilan ishlash)",
    "No-Code: Kod yozmasdan sayt tuzish",
    "QA - testing va avtomatlashtirish",
    "Project Management",
    "Android & Kotlin dasturlash",
    "PHP & Yii dasturlash",
    "Full Stack Java",
    "Node.js praktikum",
    "Robototexnika",
    "iOS & Swift dasturlash",
    "Full Stack Python",
    ".NET dasturlash",
    "UX/UI Design",
    "Front-End dasturlash",
    "English for I",
]

general_prompt = """
    Here is a conversation between a customer and an operator. The customer is interested in buying an online IT course. The operator is trying to sell the course to the customer. The conversation is in Uzbek language. According to the conversation, answer the following questions and return in json format with the following:
    Response format: {
        "is_conversation_over": true or false,
        "sentiment_analysis_of_conversation": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_operator": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_customer": "positive" or "negative" or "neutral",
        "is_customer_satisfied": true or false,
        "is_customer_agreed_to_buy": true or false,
        "is_customer_interested_to_product": true or false,
        "which_course_customer_interested": [courses_list] or None use correct course name if customer interested to product it might be multiple courses,
        "summary": "The summary of the conversation in Uzbek language with punctuation corrected and aroun 20-30 words. Summarize as checker's discretion."
        
    }
"""

openai.api_key = os.getenv("OPENAI_API_KEY")
openai.api_base = os.getenv("OPENAI_API_BASE")
openai.api_type = os.getenv("OPENAI_API_TYPE")
openai.api_version = os.getenv("OPENAI_API_VERSION")


def general_checker(text, general_prompt, courses_list, checklist=None):
    if checklist:
        prompt = checklist_prompt + "\n".join(checklist)
    else:
        prompt = general_prompt.replace("[courses_list]", str(courses_list))

    deployment_name = os.getenv("DEPLOYMENT_NAME", "gpt4")

    try:
        response = openai.ChatCompletion.create(
            deployment_id=deployment_name,
            messages=[
                {
                    "role": "system",
                    "content": prompt,
                },
                {"role": "user", "content": text},
            ],
        )

        # Assuming the response structure has the corrected text in a specific field
        corrected_text = (
            response.get("choices", [{}])[0].get("message", {}).get("content", "")
        )
        return corrected_text

    except Exception as e:
        print(f"An error occurred: {e}")
        raise e


@celery.task(base=PredictTask, track_started=True, name="api", bind=True)
def api_processing(self: PredictTask, **kwargs):
    task = kwargs.get("task", {})
    record = task.get("audio_record", {})
    checklist_id = task.get("checklist_id", None)
    general = task.get("general")
    record_payload = record.get("payload", {})
    folder_name = task.get("folder_name", "")

    if not task or not record:
        logging.error("Task data is not provided")
        raise Exception("Task data is not provided")

    file_path = os.path.join("uploads", record["storage_id"])
    if not os.path.exists(file_path):
        bucket = os.getenv("STORAGE_BUCKET_NAME", "dialixai-production")
        remote_path = f"{folder_name}/{record['storage_id']}"
        if not file_exists(remote_path):
            logging.error(f"File not found in the storage: {remote_path}")
            raise Exception(f"File not found in the storage: {remote_path}")
        download_file(bucket, remote_path, file_path)

    if not record_payload:
        logging.warning("MohirAI payload is not found in the record")
        record_payload = mohirAI(file_path)
        amount = record["duration"] * db.MOHIRAI_PRICE_PER_MS
        db.create_transaction(
            owner_id=record["owner_id"],
            record_id=record["id"],
            amount=amount,
            type="mohirai transcription",
        )
        db.upsert_record(record={**record, "payload": json.dumps(record_payload)})

    # convert conversations
    conversation = convert_to_chat(record_payload["result"]["offsets"])
    conversation_with_offset = process_transcription(
        record_payload["result"]["offsets"]
    )
    customer_id, operator_id = find_position_from_filename(file_path)

    # calculations
    operator_answer_delay = calculate_pause_duration(
        conversation_with_offset, operator_id, customer_id
    )

    operator_speech_duration = calculate_speech_duration(
        conversation_with_offset, operator_id
    )

    customer_speech_duration = calculate_speech_duration(
        conversation_with_offset, customer_id
    )

    # gpt part
    json_data = {}
    checklist_response = {}

    if general:
        gender = self.classify_speaker_gender(file_path, record["title"])
        gender = gender["result"]["gender"]
        logging.info(f"Gender detected: {gender}")
        general_response = general_checker(conversation, general_prompt, courses_list)
        db.create_transaction(
            owner_id=record["owner_id"],
            record_id=record["id"],
            amount=record["duration"] * db.GENERAL_PROMPT_PRICE_PER_MS,
            type="general prompt",
        )
        json_text = extract_json_from_markdown(general_response)
        json_data = convert_string_to_json(json_text)
        json_data.update(
            {
                "operator_answer_delay": operator_answer_delay,
                "operator_speech_duration": operator_speech_duration,
                "customer_speech_duration": customer_speech_duration,
                "customer_gender": "male",
            }
        )

    if checklist_id:
        checklist = db.get_checklist_by_id(
            checklist_id, owner_id=str(record["owner_id"])
        )
        if checklist and checklist.get("payload"):
            checklist_response = general_checker(
                conversation,
                general_prompt,
                courses_list,
                checklist=checklist.get("payload"),
            )
            db.create_transaction(
                owner_id=record["owner_id"],
                record_id=record["id"],
                amount=record["duration"] * db.CHECKLIST_PROMPT_PRICE_PER_MS,
                type="checklist prompt",
            )
        else:
            logging.warning(f"Checklist not found for id: {checklist_id}")
            checklist_response = {}

    return {
        "general_response": json_data,
        "checklist_response": checklist_response,
    }
