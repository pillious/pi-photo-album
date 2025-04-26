from dotenv import load_dotenv
import requests
import time
import json
import os

from consumer import SQSQueueConsumer

load_dotenv()

API_URL = f"http://localhost:{os.getenv('API_PORT', 5000)}"

class APIStatusException(Exception):
    pass

def main():
    sqs_consumer = SQSQueueConsumer()
    failed_health_checks = 0
    while True:
        try:
            response = requests.get(f"{API_URL}/health", timeout=10)
            if response.status_code != 200:
                raise APIStatusException(f"Status code: {response.status_code}")
            status = response.json().get('status')
            if status != 'ok':
                raise APIStatusException(f"Status not ok: {status}")
        except (requests.exceptions.RequestException, APIStatusException) as e:
            failed_health_checks += 1
            print(f"Health check failed ({failed_health_checks}): {e}")
            time.sleep(2 ** min(failed_health_checks, 5)) # exponential backoff
            continue

        print("Polling...") # DEBUG
        failed_health_checks = 0
        response = sqs_consumer.receive_messages()
        if response:
            events = []
            id_to_receipt_handles: dict[str, str] = {}

            if 'Messages' in response:
                print(f"Received messages: {response}") # DEBUG
            for sqs_message in response.get('Messages', []):
                id_to_receipt_handles[sqs_message['MessageId']] = sqs_message['ReceiptHandle']

                body = json.loads(sqs_message['Body'])
                message = json.loads(body['Message'])
                events.extend(message['events'])

            if events:
                try:
                    response = requests.post(f"{API_URL}/receive-events", json={"events": events}, timeout=10)
                    if response.status_code != 200:
                        raise APIStatusException(f"Status code: {response.status_code}")
                    status = response.json().get('status')
                    if status != 'ok':
                        raise APIStatusException(f"Status not ok: {status}")
                except (requests.exceptions.RequestException, APIStatusException) as e:
                    print(f"Error sending messages to API: {e}")
                    time.sleep(10) # Wait for the full length of sqs VISIBILITY_TIMEOUT
                    continue
                sqs_consumer.delete_messages(id_to_receipt_handles)

if __name__ == "__main__":
    main()