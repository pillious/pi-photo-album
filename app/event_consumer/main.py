import botocore.exceptions
import requests
import time
import json
import botocore
import os
import threading

from app.config.config import config, load_config
from app.utils import utils, aws, pending
from app.event_consumer.consumer import SQSQueueConsumer

utils.load_env([".env", os.path.abspath(os.path.expandvars('$HOME/.config/pi-photo-album/.env'))])
load_config()

def main():
    sqs_consumer = SQSQueueConsumer()
    failed_health_checks = 0
    resync_thread = None
    resync_result = {"ok": False}
    while True:
        if not is_api_healthy():
            if failed_health_checks == 0:
                print("API is not healthy. Waiting for it to come back online...")
            failed_health_checks += 1
            time.sleep(2 ** min(failed_health_checks, 5)) # exponential backoff
            continue

        if resync_thread is not None and resync_thread.is_alive():
            print("Resync already in progress. Skipping...")
            time.sleep(5)
            continue

        if resync_thread is not None:
            if resync_result["ok"]:
                pending.write_poll_time()
                time.sleep(30)
            else:
                print("Error sending resync request.")
                time.sleep(5)
            resync_thread = None
            continue

        if not pending.is_within_retention_period():
            print("Retention period expired. Sending resync request...")
            resync_result = {"ok": False}
            resync_thread = threading.Thread(
                target=_run_resync,
                args=(resync_result,),
                daemon=True,
            )
            resync_thread.start()
            continue

        try:
            # Check if the SQS queue is healthy
            if not aws.ping(config()['url']['sqs_ping_url'].as_str()):
                handle_consumer_offline()
                failed_health_checks += 1
                time.sleep(2 ** min(failed_health_checks, 5))
                continue

            response = sqs_consumer.receive_messages()
            if response:
                events = []
                # mapping (msg id -> receipt handle) required to delete messages from queue
                id_to_receipt_handles: dict[str, str] = {}

                messages = response.get('Messages', [])
                if len(messages) > 0:
                    print(f"Received {len(response.get('Messages', []))} messages.")

                # We can receive multiple messages in one response
                for sqs_message in messages:
                    id_to_receipt_handles[sqs_message['MessageId']] = sqs_message['ReceiptHandle']

                    body = json.loads(sqs_message['Body'])
                    message = json.loads(body['Message'])
                    events.extend(message['events'])

                if events:
                    if not send_events(events):
                        time.sleep(10) # Wait for the full length of sqs VISIBILITY_TIMEOUT
                        continue
                    sqs_consumer.delete_messages(id_to_receipt_handles)
            pending.write_poll_time()
        except botocore.exceptions.ConnectionError as e:
            print("Connection error.")
            handle_consumer_offline()
        failed_health_checks = 0


def is_api_healthy():
    """
    Check the health of the API.
    """
    try:
        api_url = config()['url']['api_url'].as_str()
        response = requests.get(f"{api_url}/health", timeout=10)
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
        api_url = config()['url']['api_url'].as_str()
        response = requests.post(f"{api_url}/receive-events", json={"events": events}, timeout=10)
        if response.status_code != 200:
            return False
        status = response.json().get('status')
        if status != 'ok':
            return False
    except Exception as e:
        print(f"Error sending messages to API: {e}")
        return False
    return True

def _run_resync(result):
    result["ok"] = send_resync_request()

def send_resync_request():
    """
    Send a resync filesystem request to the API.
    Blocks until the API finishes resyncing.
    """
    try:
        api_url = config()['url']['api_url'].as_str()
        response = requests.post(f"{api_url}/resync", timeout=None)
        if response.status_code != 200:
            return False
        status = response.json().get('status')
        if status != 'ok':
            return False
    except Exception:
        return False
    return True

def handle_consumer_offline():
    if pending.get_last_poll() != pending.get_snapshot_time():
        print("Went offline. Saving file system snapshot.")
        fs_snapshot_file = config()['paths']['fs_snapshot_file'].as_str()
        pending.save_simple_fs_snapshot(fs_snapshot_file)

if __name__ == "__main__":
    os.makedirs(config()['paths']['config_dir'].as_str(), exist_ok=True)

    main()