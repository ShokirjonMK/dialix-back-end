import os
import json
import time
import logging

import openai

from decouple import config
import openai.error

from backend.core import settings
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
    You are given a conversation between a call center operator and a potential customer. 
    The operator should ask certain questions from the list below, organized by segments. 
    Your task is to identify if each question is asked or not within each segment. 
    If a question is asked, return "question content": true; if not asked, return "question content": false.
    Response format:
    {
        "segment_title 1": {
            "Question 1": true or false, # true if asked, false if not asked
            "Question 2": true or false  # true if asked, false if not asked
        },
        "segment_title 2": {
            "Question 3": true or false, # true if asked, false if not asked
            "Question 4": true or false  # true if asked, false if not asked
        }
    }
    Request format for checklist would be:
    {
        "segment_title 1": ["Question 1", "Question 2"],
        "segment_title 2": ["Question 3", "Question 4"]
    }
    Here is the list of real segments and their respective questions:
"""

courses_list = [
    "Kiberxavfsizlik: Pentesting",
    "Computer Vision",
    "Data Science va Sun'iy Intellekt",
    "Sun'iy intellekt - NLP (nutq bilan ishlash)",
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
    "English for IT",
]

general_prompt = """
    Here is a conversation between a customer and an operator. The customer is interested in buying an online IT course. The operator is trying to sell the course to the customer. The conversation is in Uzbek language. According to the conversation, answer the following questions and return in json format with the following:
    Response format: {
    "is_conversation_over": true or false,
    "call_purpose": "Clients call for a specific purpose. Sometimes, their purpose could be purchasing the product. Choose only one. Because each call has only one purpose. Clients call for the following purposes: Ma'lumot olish, Pulni Qaytarish, Kurs sotib olish, Texnik muammo, To'lov masalasi, Dars sifati",
    "sentiment_analysis_of_conversation": "positive" or "negative" or "neutral",
    "reason_for_conversation_sentiment": "Detailed explanation in Uzbek within 30 words. Provide clear improvement steps if negative sentiment.",
    "sentiment_analysis_of_operator": "positive" or "negative" or "neutral",
    "reason_for_operator_sentiment": "Detailed explanation in Uzbek within 30 words. Provide clear improvement steps if negative sentiment.",
    "list_of_words_define_operator_sentiment": ["word1", "word2", "word3", "word4", "word5"] or None,
    "sentiment_analysis_of_customer": "positive" or "negative" or "neutral",
    "reason_for_customer_sentiment": "Detailed explanation in Uzbek within 30 words. Provide clear improvement steps if negative sentiment.",
    "list_of_words_define_customer_sentiment": ["word1", "word2", "word3", "word4", "word5"] or None,
    "is_customer_satisfied": true or false,
    "is_customer_agreed_to_buy": true or false,
    "reason_for_customer_purchase": "Reason for decision in 50 words (flexible by a few words if needed).",
    "is_customer_interested_to_product": true or false,
    "how_old_is_customer": integer or None,
    "which_course_customer_interested": ["course1", "course2"] or None,  // Use exact course names if available,
    "which_platform_customer_found_about_the_course": "Facebook" or "Instagram" or "Telegram" or "Banners" or "Relatives" or "Friends" or None,
    "summary": "Uzbek language summary, punctuated correctly, around 50 words."
}

"""
deployment_name: str = config("DEPLOYMENT_NAME", default="gpt4")

openai.api_key = config("OPENAI_API_KEY")
openai.api_base = config("OPENAI_API_BASE")
openai.api_type = config("OPENAI_API_TYPE")
openai.api_version = config("OPENAI_API_VERSION")


def make_gpt_request(deployment_name: str, prompt: str, text: str) -> str:
    response = openai.ChatCompletion.create(
        deployment_id=deployment_name,
        messages=[
            {
                "role": "system",
                "content": prompt,
            },
            {"role": "user", "content": text},
        ],
        temperature=0.7,
    )

    corrected_text: str = (
        response.get("choices", [{}])[0].get("message", {}).get("content", "")
    )

    try:
        corrected_text = corrected_text.strip().replace("`", "'")
    except Exception as exc:
        logging.error(f"Failed to correct text: {corrected_text=} {exc=}")
        raise exc

    return corrected_text


def general_checker(
    text: str, general_prompt: str, courses_list, checklist=None
) -> str:
    global deployment_name

    backoff_time: int = 1

    if checklist:
        prompt = checklist_prompt + "\n" + json.dumps(checklist)
    else:
        prompt = general_prompt.replace("[courses_list]", str(courses_list))

    logging.info(f"Making request with {prompt=}")

    while True:
        try:
            corrected_text = make_gpt_request(deployment_name, prompt, text)
            return corrected_text
        except openai.error.RateLimitError as exc:
            logging.info(f"Rate limit exc: {exc=} {backoff_time=}")
            time.sleep(backoff_time)
            backoff_time = min(backoff_time * 2, 60)


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
        bucket = config("STORAGE_BUCKET_NAME", default="dialixai-production")
        remote_path = f"{folder_name}/{record['storage_id']}"
        if not file_exists(remote_path):
            logging.error(f"File not found in the storage: {remote_path}")
            raise Exception(f"File not found in the storage: {remote_path}")
        download_file(bucket, remote_path, file_path)

    if not record_payload:
        logging.warning("MohirAI payload is not found in the record")
        record_payload = mohirAI(file_path)
        amount = record["duration"] * settings.MOHIRAI_PRICE_PER_MS
        logging.info(f"[TRANSACTION] MohirAI price {amount=}")
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
        logging.info(
            f"[TRANSACTION] General price {record['duration'] * settings.GENERAL_PROMPT_PRICE_PER_MS}"
        )
        db.create_transaction(
            owner_id=record["owner_id"],
            record_id=record["id"],
            amount=record["duration"] * settings.GENERAL_PROMPT_PRICE_PER_MS,
            type="general prompt",
        )
        json_text = extract_json_from_markdown(general_response)
        json_data = convert_string_to_json(json_text)
        json_data.update(
            {
                "operator_answer_delay": operator_answer_delay,
                "operator_speech_duration": operator_speech_duration,
                "customer_speech_duration": customer_speech_duration,
                "customer_gender": gender,
            }
        )
    else:
        logging.info(f"Will not process via general for {file_path=} coz {general=}")

    if checklist_id and checklist_id is not None:
        checklist = db.get_checklist_by_id(
            checklist_id, owner_id=str(record["owner_id"])
        )

        logging.info(f"Checklist from db: {checklist=}")

        if checklist and checklist.get("payload"):
            checklist_response = general_checker(
                conversation,
                checklist_prompt,
                courses_list,
                checklist=checklist.get("payload"),
            )
            logging.info(
                f"[TRANSACTION] Checklist price: {record['duration'] * settings.CHECKLIST_PROMPT_PRICE_PER_MS}"
            )
            db.create_transaction(
                owner_id=record["owner_id"],
                record_id=record["id"],
                amount=record["duration"] * settings.CHECKLIST_PROMPT_PRICE_PER_MS,
                type="checklist prompt",
            )
        else:
            logging.warning(f"Checklist not found for id: {checklist_id}")
            checklist_response = {}
    else:
        logging.info(
            f"Will not process via checklist for {file_path=} coz {checklist_id=}"
        )

    return {"general_response": json_data, "checklist_response": checklist_response}
