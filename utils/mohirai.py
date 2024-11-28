import time
import logging
import requests
from pydub import AudioSegment
from ratelimit import limits, sleep_and_retry

from backend.core import settings


def calculate_sleep_time(duration_minutes):
    if 0 <= duration_minutes <= 4:
        return 5
    elif 5 <= duration_minutes < 10:
        return 10
    elif 10 <= duration_minutes < 15:
        return 20
    elif 15 <= duration_minutes < 20:
        return 30
    elif duration_minutes >= 20:
        return 45
    return 8


@sleep_and_retry
@limits(calls=5, period=60)
def mohirAI(file_path):
    logging.warning(f"Processing file in mohirAI function: {file_path}")
    api_key = settings.MOHIRAI_API_KEY

    url = "https://uzbekvoice.ai/api/v1/stt"
    headers = {"Authorization": api_key}

    files = {"file": ("audio.mp3", open(file_path, "rb"))}
    data = {
        "return_offsets": "true",
        "run_diarization": "true",
        "language": "uz",
        "blocking": "false",
    }

    audio = AudioSegment.from_file(file_path)
    duration_ms = len(audio)
    duration_minutes = duration_ms / 60000
    poll_interval = calculate_sleep_time(duration_minutes)

    print(f"Audio length: {duration_minutes:.2f} minutes")
    print(f"Poll interval (sleep time): {poll_interval} seconds")

    try:
        general_response = requests.post(url, headers=headers, files=files, data=data)
        print("General Response is now printing")
        print(general_response)
        if general_response.status_code != 200:
            logging.error(
                f"Request failed with status code {general_response.status_code}: {general_response.text}"
            )
            general_response.raise_for_status()

        response_data = general_response.json()
        task_id = response_data["id"]

        print("response data")
        print(response_data)
        task_id_temp = response_data["id"]
        print("Temp resp data")
        print(task_id_temp)

        url = f"https://uzbekvoice.ai/api/v1/tasks?id={task_id}"
        headers = {"Authorization": api_key, "Content-Type": "application/json"}

        while True:
            print("Started sleeping")
            time.sleep(poll_interval)
            print("Sleep end")
            response = requests.get(url, headers=headers)
            print("Task polling result")
            print(response)
            result = response.json()
            print("Print data for ID from result")
            print(result)
            if response.status_code == 200:
                if result["status"] == "SUCCESS":
                    return result
            elif response.status_code in [404, 408, 500]:
                logging.error(
                    f"Task {task_id} failed with code:{response.status_code} and body:{result}"
                )
                raise Exception(
                    f"Task {task_id} failed with code:{response.status_code}"
                )
            else:
                logging.warning(
                    f"Request failed with status code {response.status_code}: {response.text}"
                )
                response.raise_for_status()

    except requests.exceptions.RequestException as e:
        logging.error(f"MohirAI request failed: {e}")
        raise e
