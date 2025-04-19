from abc import ABC, abstractmethod
import boto3
import os
from dotenv import load_dotenv

# from utils import get_aws_autorefresh_session

load_dotenv()

def main():
    sqs_consumer = SQSQueueConsumer()

    while True:
        print("Polling for messages...")
        # poll to check if the api is online before consuming events
        # need somekind of health check endpoint

        messages = sqs_consumer.recieveMessages()
        if messages:
            for message in messages.get('Messages', []):
                print(f"Received message: {message['Body']}")
                # Process the message here
                # TODO ... 
                # Delete the message after processing
                sqs_consumer.deleteMessage(message['ReceiptHandle'])


class QueueConsumer(ABC):
    @abstractmethod
    def recieveMessages(self):
        pass

    @abstractmethod
    def deleteMessage(self, receiptHandles):
        pass

class SQSQueueConsumer(QueueConsumer):
    def __init__(self):
        self.sqs_client = boto3.client(
            'sqs', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

        self.queue_url = os.getenv('RECEIVE_EVENT_QUEUE_URL')

        self.MAX_POLLING_INTERVAL = 20 # 20 sec max allowed by sqs
        self.MAX_MESSAGES = 10 # 10 messages max allowed by sqs
        self.VISIBILITY_TIMEOUT = 30

        # autorefresh_session, _ = get_aws_autorefresh_session(os.getenv('RECEIVE_EVENT_QUEUE_ROLE'), "receive-event-queue-session")
        # self.sqs_client = autorefresh_session.client('sqs')

    def recieveMessages(self):
        return self.sqs_client.receive_message(
            QueueUrl=self.queue_url,
            MessageAttributeNames=['All'],
            MaxNumberOfMessages=self.MAX_MESSAGES,
            VisibilityTimeout=self.VISIBILITY_TIMEOUT,
            WaitTimeSeconds=self.MAX_POLLING_INTERVAL
        )
    
    def deleteMessage(self, receiptHandle):
        return self.sqs_client.delete_message(
            QueueUrl=self.queue_url,
            ReceiptHandle=receiptHandle
        )

if __name__ == "__main__":
    main()