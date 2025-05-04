import botocore.exceptions
from dotenv import load_dotenv
import datetime
import requests
import time
import json
import os
import botocore

import app.globals as globals
import app.utils.offline as offline
from app.event_consumer.consumer import SQSQueueConsumer


load_dotenv()

API_URL = f"http://localhost:{os.getenv('API_PORT', 5000)}"

class APIStatusException(Exception):
    pass

def main():
    sqs_consumer = SQSQueueConsumer()
    failed_health_checks = 0
    while True:
        try:
            api_health_check()
        except (requests.exceptions.RequestException, APIStatusException) as e:
            failed_health_checks += 1
            print(f"Health check failed ({failed_health_checks}): {e}")
            time.sleep(2 ** min(failed_health_checks, 5)) # exponential backoff
            continue

        # if not is_within_retention_period():
        #     print("Retention period expired. Sending resync request...")
        #     send_resync_request()
        #     write_curr_timestamp() # TODO: only write if resync was successful
        #     time.sleep(30) # Wait for the resync to complete
        #     continue

        print("Polling...") # DEBUG
        failed_health_checks = 0
        try:
            # raise(botocore.exceptions.ConnectionError(error="TESTING")) # DEBUG

            response = sqs_consumer.receive_messages()
            if response:
                events = []
                # mapping (msg id -> receipt handle) required to delete messages from queue
                id_to_receipt_handles: dict[str, str] = {}

                if 'Messages' in response:
                    print(f"Received messages: {response}") # DEBUG
                # We can receive multiple messages in one response
                for sqs_message in response.get('Messages', []):
                    id_to_receipt_handles[sqs_message['MessageId']] = sqs_message['ReceiptHandle']

                    body = json.loads(sqs_message['Body'])
                    message = json.loads(body['Message'])
                    events.extend(message['events'])

                if events:
                    try:
                        send_events(events)
                    except (requests.exceptions.RequestException, APIStatusException) as e:
                        print(f"Error sending messages to API: {e}")
                        time.sleep(10) # Wait for the full length of sqs VISIBILITY_TIMEOUT
                        continue
                    sqs_consumer.delete_messages(id_to_receipt_handles)
            offline.write_poll_time()
        except botocore.exceptions.ConnectionError as e:
            print("Connection error.")
            if offline.get_last_poll() != offline.get_snapshot_time():
                print("Went offline. Saving file system snapshot.")
                offline.save_simple_fs_snapshot(globals.FS_SNAPSHOT_FILE)
            time.sleep(5)

def api_health_check():
    """
    Check the health of the API.
    - Raises `APIStatusException` if the API is not healthy.
    - Raises `requests.exceptions.RequestException` for network-related errors.
    """
    response = requests.get(f"{API_URL}/health", timeout=10)
    if response.status_code != 200:
        raise APIStatusException(f"Status code: {response.status_code}")
    status = response.json().get('status')
    if status != 'ok':
        raise APIStatusException(f"Status not ok: {status}")

def send_events(events):
    """
    Send events to the API.
    - Raises `APIStatusException` if the request fails.
    - Raises `requests.exceptions.RequestException` for network-related errors.
    """
    response = requests.post(f"{API_URL}/receive-events", json={"events": events}, timeout=10)
    if response.status_code != 200:
        raise APIStatusException(f"Status code: {response.status_code}")
    status = response.json().get('status')
    if status != 'ok':
        raise APIStatusException(f"Status not ok: {status}")

def send_resync_request():
    """
    Send a resync filesystem request to the API.
    - Raises `APIStatusException` if the request fails.
    - Raises `requests.exceptions.RequestException` for network-related errors.
    """
    response = requests.post(f"{API_URL}/resync", timeout=10)
    if response.status_code != 200:
        raise APIStatusException(f"Status code: {response.status_code}")
    status = response.json().get('status')
    if status != 'ok':
        raise APIStatusException(f"Status not ok: {status}")

if __name__ == "__main__":
    main()