import botocore.exceptions
from dotenv import load_dotenv
import datetime
import requests
import time
import json
import os
import botocore

import app.globals as globals
import app.utils.aws as aws
import app.utils.offline as offline
from app.event_consumer.consumer import SQSQueueConsumer


load_dotenv()

def main():
    sqs_consumer = SQSQueueConsumer()
    failed_health_checks = 0
    while True:
        if not is_api_healthy():
            failed_health_checks += 1
            print(f"Health check failed ({failed_health_checks})")
            time.sleep(2 ** min(failed_health_checks, 5)) # exponential backoff
            continue

        if not offline.is_within_retention_period():
            print("Retention period expired. Sending resync request...")
            if not send_resync_request():
                print("Error sending resync request.")
                continue
            offline.write_poll_time()
            time.sleep(30) # Wait for the resync to complete
            continue

        print("Polling...") # DEBUG
        try:
            # Check if the SQS queue is healthy
            if not aws.ping(globals.SQS_PING_URL):
                handle_consumer_offline()
                failed_health_checks += 1
                time.sleep(2 ** min(failed_health_checks, 5))
                continue
        
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
                    if not send_events(events):
                        print(f"Error sending messages to API: {e}")
                        time.sleep(10) # Wait for the full length of sqs VISIBILITY_TIMEOUT
                        continue
                    sqs_consumer.delete_messages(id_to_receipt_handles)
            offline.write_poll_time()
        except botocore.exceptions.ConnectionError as e:
            print("Connection error.")
            handle_consumer_offline()
        failed_health_checks = 0


def is_api_healthy():
    """
    Check the health of the API.
    """
    try:
        response = requests.get(f"{globals.API_URL}/health", timeout=10)
        if response.status_code != 200:
            return False
        status = response.json().get('status')
        if status != 'ok':
            return False
    except Exception:
        return False
    return True

def send_events(events):
    """
    Send events to the API.
    """
    try:
        response = requests.post(f"{globals.API_URL}/receive-events", json={"events": events}, timeout=10)
        if response.status_code != 200:
            return False
        status = response.json().get('status')
        if status != 'ok':
            return False
    except Exception:
        return False
    return True

def send_resync_request():
    """
    Send a resync filesystem request to the API.
    """
    try:
        response = requests.post(f"{globals.API_URL}/resync", timeout=10)
        if response.status_code != 200:
            return False
        status = response.json().get('status')
        if status != 'ok':
            return False
    except Exception:
        return False
    return True

def handle_consumer_offline():
    if offline.get_last_poll() != offline.get_snapshot_time():
        print("Went offline. Saving file system snapshot.")
        offline.save_simple_fs_snapshot(globals.FS_SNAPSHOT_FILE)

if __name__ == "__main__":
    main()