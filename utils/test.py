import logging

import openai
from glob import glob
import time
import os
import json
import re
import requests


openai.api_key = "ba6117836c5347338b49a5092035c2fa"
openai.api_base = "https://mohir-temp-punct.openai.azure.com/"  # your endpoint should look like the following https://YOUR_RESOURCE_NAME.openai.azure.com/
openai.api_type = "azure"
openai.api_version = "2023-05-15"
api_key = "be314780-cd12-4c8a-acca-e39cde624618:491524e0-f338-466a-9320-219acef929bf"


prompt = """
    Here is a conversation between a customer and an operator. The customer is interested in buying an online IT course. The operator is trying to sell the course to the customer. The conversation is in Uzbek language. According to the conversation, answer the following questions and return in json format with the following:
    Response format: {
        "is_conversation_over": true or false,
        "sentiment_analysis_of_conversation": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_operator": "positive" or "negative" or "neutral",
        "sentiment_analysis_of_customer": "positive" or "negative" or "neutral",
        "is_customer_satisfied": true or false,
        "is_customer_agreed_to_buy": true or false,
        "is_customer_interested_to_product": true or false,
        "which_course_customer_interested": "[
            Kiberxavfsizlik: Pentesting,
            Computer Vision,
            Data Science va Sun'iy Intellekt,
            Sunʼiy intellekt - NLP (nutq bilan ishlash),
            No-Code: Kod yozmasdan sayt tuzish,
            QA - testing va avtomatlashtirish,
            Project Management,
            Android & Kotlin dasturlash,
            PHP & Yii dasturlash,
            Full Stack Java,
            Node.js praktikum,
            Robototexnika,
            iOS & Swift dasturlash,
            Full Stack Python,
            .NET dasturlash,
            UX/UI Design,
            Front-End dasturlash,
            English for IT
        ]" or None use correct course name if customer interested to product it might be multiple courses,
        "summary": "The summary of the conversation in Uzbek language with punctuation corrected and aroun 20-30 words. Summarize as checker's discretion."
        
    }
"""


def mohirAI(api_key, file_path):
    url = "https://mohir.ai/api/v1/stt"
    headers = {"Authorization": api_key}

    files = {
        "file": ("audio.mp3", open(file_path, "rb")),
    }
    data = {
        "return_offsets": "true",
        "run_diarization": "true",
        "blocking": "false",
    }

    try:
        response_1 = requests.post(url, headers=headers, files=files, data=data)
        time.sleep(15)
        response = requests.get(
            f"https://mohir.ai/api/v1/tasks?id={response_1.json()['id']}",
            headers=headers,
        )
        if response.status_code == 200:
            with open("response.json", "w") as f:
                f.write(response.text)
            return response.json()
        else:
            return f"Request failed with status code {response.status_code}: {response.text}"
    except requests.exceptions.Timeout:
        return "Request timed out. The API response took too long to arrive."


def request_to_gpt(text, prompt):
    """
    Corrects punctuation in Uzbek language text.

    Parameters:
    - text (str): The input text in Uzbek that needs punctuation correction.

    Returns:
    - str: The corrected text.
    """

    deployment_name = os.getenv(
        "DEPLOYMENT_NAME", "gpt4"
    )  # Replace with your actual deployment ID

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
        return text


def extract_specific_part(input_str):
    # Pattern to match the desired format
    pattern = r"\d{4}-\d{2}-\d{2}_\[\d{2}_\d{2}_\d{2}\]_\d+_\d+"

    # Search for the pattern in the input string
    match = re.search(pattern, input_str)

    if match:
        return match.group(0)  # Return the matched part of the string
    else:
        return ""  # Return an empty string if no match is found


def convert_string_to_json(input_str):
    try:
        json_data = json.loads(input_str)
        return json_data
    except json.JSONDecodeError as e:
        return {"error": f"Failed to decode JSON: {str(e)}"}


def extract_json_from_markdown(input_str):
    # Trim the markdown code block syntax and any leading/trailing whitespace
    trimmed_str = input_str.strip("` \n")

    # Use regular expressions to extract JSON text within the curly braces, including nested braces
    pattern = r"\{[\s\S]*?\}"
    match = re.search(pattern, trimmed_str)

    if match:
        return match.group(0)  # Return the matched JSON string
    else:
        return ""


def convert_to_chat(data):
    chat = ""
    current_speaker = None

    for segment in data:
        speaker_id = segment["speaker"]
        word = segment["word"]

        # Check if the speaker has changed
        if current_speaker != speaker_id:
            current_speaker = speaker_id
            chat += f"\nSpeaker {speaker_id}: "

        chat += word + " "

    return chat.strip()


def process_transcription(data):
    # Initialize a list to hold the structured conversation
    structured_conversation = []

    # Temporary storage for accumulating words for the current speaker
    current_speaker = None
    current_text = []
    start_time = None
    end_time = None

    for item in data:
        # Check if we are still on the same speaker or if this is the first item
        if current_speaker is None or item["speaker"] == current_speaker:
            # Update the current speaker if this is the first word
            if current_speaker is None:
                current_speaker = item["speaker"]
                start_time = item["start"]

            # Append the word to the current text
            current_text.append(item["word"])
            end_time = item["end"]
        else:
            # Append the accumulated words for the previous speaker to the structured conversation
            structured_conversation.append(
                {
                    "speaker": current_speaker,
                    "text": " ".join(current_text),
                    "start": start_time,
                    "end": end_time,
                }
            )

            # Reset for the new speaker
            current_speaker = item["speaker"]
            current_text = [item["word"]]
            start_time = item["start"]
            end_time = item["end"]

    # Don't forget to add the last speaker's words if any
    if current_text:
        structured_conversation.append(
            {
                "speaker": current_speaker,
                "text": " ".join(current_text),
                "start": start_time,
                "end": end_time,
            }
        )

    return structured_conversation


def calculate_pause_duration(conversations, operator, customer):
    total_pause_duration = 0
    last_customer_end_time = None

    for conversation in conversations:
        if conversation["speaker"] == customer:  # If current speaker is the customer
            last_customer_end_time = conversation["end"]
        elif (
            conversation["speaker"] == operator and last_customer_end_time is not None
        ):  # If current speaker is the operator and customer spoke before
            pause_duration = conversation["start"] - last_customer_end_time
            total_pause_duration += pause_duration
            last_customer_end_time = None  # Reset after calculating pause

    return total_pause_duration


def calculate_speech_duration(conversations, speaker_id):
    total_speech_duration = 0

    for conversation in conversations:
        if conversation["speaker"] == speaker_id:
            speech_duration = conversation["end"] - conversation["start"]
            total_speech_duration += speech_duration

    return total_speech_duration


def find_position_from_filename(file_path):
    try:
        # Extract the relevant part of the file name (assuming the last part after the last '/')
        file_name = file_path.split("/")[-1]

        # Extract numbers (assuming they are separated by underscores)
        parts = file_name.split("_")

        # Extract the phone number and operator number based on their position
        number_1 = parts[-1]
        number_2 = parts[-2]

        # Determine speaker IDs based on the order
        if len(number_1) < len(number_2):
            return 0, 1
        else:
            return 1, 0
    except Exception as e:
        return 0, 1


def get_info_from_conversation(file_path, prompt=prompt):
    try:
        time.sleep(15)
        result = mohirAI(api_key, file_path)
        conversation = convert_to_chat(result["result"]["offsets"])
        with open("conversation.json", "w") as f:
            f.write(json.dumps(result))
        conversation_with_offset = process_transcription(result["result"]["offsets"])
        with open("conversation_with_offset.json", "w") as f:
            f.write(json.dumps(conversation_with_offset))

        customer_id, operator_id = find_position_from_filename(file_path)
        with open("customer_operator.json", "w") as f:
            f.write(
                json.dumps({"customer_id": customer_id, "operator_id": operator_id})
            )

        operator_answer_delay = calculate_pause_duration(
            conversation_with_offset, operator_id, customer_id
        )
        print(f"Operator answer delay: {operator_answer_delay}")
        operator_speech_duration = calculate_speech_duration(
            conversation_with_offset, operator_id
        )
        print(f"Operator speech duration: {operator_speech_duration}")
        customer_speech_duration = calculate_speech_duration(
            conversation_with_offset, customer_id
        )
        print(f"Customer speech duration: {customer_speech_duration}")

        gpt_response = request_to_gpt(conversation, prompt)
        with open("gpt_response.json", "w") as f:
            f.write(gpt_response)
        json_text = extract_json_from_markdown(gpt_response)
        print(f"Extracted JSON: {json_text}")
        json_data = convert_string_to_json(json_text)
        with open("json_data.json", "w") as f:
            f.write(json.dumps(json_data))
        json_data.update(
            {
                "operator_answer_delay": operator_answer_delay,
                "operator_speech_duration": operator_speech_duration,
                "customer_speech_duration": customer_speech_duration,
                # "conversation": conversation
            }
        )
        with open("json_data_2.json", "w") as f:
            f.write(json.dumps(json_data))
        return json_data
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"An error occurred: {e}")
        return {
            "operator_answer_delay": None,
            "operator_speech_duration": None,
            "customer_speech_duration": None,
            "is_conversation_over": None,
            "sentiment_analysis_of_conversation": None,
            "sentiment_analysis_of_operator": None,
            "sentiment_analysis_of_customer": None,
            "is_customer_satisfied": None,
            "is_customer_agreed_to_buy": None,
            "is_customer_interested_to_product": None,
            "summary": None,
            # "conversation": None
        }


def process(path):
    info = get_info_from_conversation(path, prompt=prompt)
    return info
