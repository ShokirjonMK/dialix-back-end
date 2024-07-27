import logging
import json
import re


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


def find_operator_code(title):
    parts = title.split("_")

    number_1 = parts[-1].split(".")[0]
    number_2 = parts[-2]

    if len(number_1) == 3:
        operator_code = number_1
    elif len(number_2) == 3:
        operator_code = number_2
    else:
        operator_code = None
    return operator_code


def find_call_type(title):
    # Extract numbers (assuming they are separated by underscores)
    parts = title.split("_")

    # Extract the phone number and operator number based on their position
    number_1 = parts[-1].split(".")[0]  # Removing the file extension if any
    number_2 = parts[-2]

    # Determine if the call is inbound or outbound
    if len(number_1) == 3:
        return "inbound"
    elif len(number_2) == 3:
        return "outbound"
    else:
        return "unknown"  # Default in case the format is unexpected
