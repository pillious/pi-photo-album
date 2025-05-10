from abc import ABC, abstractmethod
import boto3
import botocore
import os
import time
import requests

import botocore.config


class QueueConsumer(ABC):
    @abstractmethod
    def receive_messages(self) -> dict | None:
        '''
        Receives messages from the queue.
        Returns:
            A dictionary containing the received messages or None if an error occurs.
        '''
        pass

    @abstractmethod
    def delete_messages(self, id_to_receipt_handles: dict[str, str], max_retries: int) -> dict[str, str]:
        '''
        Deletes messages from the queue.
        Args:
            id_to_receipt_handles (dict[str, str]): A dictionary mapping message IDs to receipt handles.
            max_retries (int): The maximum number of retries for deleting messages.
        Returns:
            dict[str, str]: A dictionary of message IDs that were not deleted.
        '''
        pass

class SQSQueueConsumer(QueueConsumer):
    def __init__(self):
        self.MAX_POLLING_INTERVAL = 20 # 20 sec max allowed by sqs
        self.MAX_MESSAGES = 10 # 10 messages max allowed by sqs
        self.VISIBILITY_TIMEOUT = 10

        self.sqs_client = boto3.client(
            'sqs', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION'),
            config=botocore.config.Config(
                connect_timeout=2,
                read_timeout=self.MAX_POLLING_INTERVAL + 2,
                retries={'total_max_attempts': 1} # Don't retry
            )
        )

    def receive_messages(self):
        try:
            return self.sqs_client.receive_message(
                QueueUrl=os.getenv('RECEIVE_EVENT_QUEUE_URL'),
                MessageAttributeNames=['All'],
                MaxNumberOfMessages=self.MAX_MESSAGES,
                VisibilityTimeout=self.VISIBILITY_TIMEOUT,
                WaitTimeSeconds=self.MAX_POLLING_INTERVAL
            )
        except Exception as e:
            print(f"Error reading from queue: {e}")
            return None

    def delete_messages(self, id_to_receipt_handles, max_retries = 2):
        id_to_rh = id_to_receipt_handles.copy()
        for retry in range(max_retries+1):
            if not id_to_rh:
                break
            
            entries = [{'Id': ID, 'ReceiptHandle': rh} for ID, rh in id_to_rh.items()]

            try:
                response = self.sqs_client.delete_message_batch(
                    QueueUrl=os.getenv('RECEIVE_EVENT_QUEUE_URL'),
                    Entries=entries
                )
                print(f"Delete response: {response}") # DEBUG
                for entry in response.get('Successful', []):
                    del id_to_rh[entry['Id']]
                failed = response.get('Failed', [])
                if failed:
                    print(f"Failed to delete messages from queue (Attempt {retry+1}/{max_retries+1}): {failed}")
            except Exception as e:
                print(f"Error deleting messages from queue (Attempt {retry+1}/{max_retries+1}): {e}")
            
            time.sleep(2 ** retry) # exponential backoff

        return id_to_rh