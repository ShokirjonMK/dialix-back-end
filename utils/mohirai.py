import logging
import os
import time
import requests
from ratelimit import limits, sleep_and_retry


@sleep_and_retry
@limits(calls=5, period=60)
def mohirAI(file_path):
    logging.warning(f"Processing file in mohirAI function: {file_path}")
    api_key = "da7c8191-3842-4d4f-bba8-6867aaaac663:7948f6e2-b1ca-4df1-8a2a-9c5f7828172c"
    url = 'https://uzbekvoice.ai/api/v1/stt'
    headers = {
        "Authorization": api_key
    }

    files = {
        "file": ("audio.mp3", open(file_path, "rb")),
    }
    data = {
        "return_offsets": "true",
        "run_diarization": "true",
        "language": "uz",
        "blocking": "false",
    }

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
        task_id_temp= response_data['id']
        print("Temp resp data")
        print(task_id_temp)
        poll_interval = 15  # Check every 10 seconds
        url = f'https://uzbekvoice.ai/api/v1/tasks?id={task_id}'
        headers = {
            'Authorization': api_key,
            'Content-Type': 'application/json'
        }
        while True:
            print("Started sleeping")
            time.sleep(15)
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
                time.sleep(poll_interval)
            elif (
                response.status_code == 404
                or response.status_code == 408
                or response.status_code == 500
            ):
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