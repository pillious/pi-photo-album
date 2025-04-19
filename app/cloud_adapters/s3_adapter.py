from typing import List, Tuple
import boto3
import os
import concurrent.futures

from utils import get_aws_autorefresh_session
from cloud_adapters.adapter import Adapter
from cloud_adapters.exceptions import AdapterException

class S3Adapter(Adapter):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION')
        )

        autorefresh_session, _ = get_aws_autorefresh_session(os.getenv('PUSH_QUEUE_ROLE'), "push-queue-session")
        self.sqs_client = autorefresh_session.client('sqs', region_name=os.getenv('AWS_REGION'))

    def get_album(self, album_path):
        pass

    def get(self, image_key: str) -> bytes:
        try:
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=image_key)
            return obj['Body'].read()
        except Exception as e:
            AdapterException(f"Error getting image from S3: {e}")

    def insert(self, image_path: str, image_key: str) -> bool:
        print(f"Uploading {image_path} to {image_key}")
        try:
            return self.s3_client.upload_file(Bucket=self.bucket_name, Filename=image_path, Key=image_key)
        except Exception as e:
            raise AdapterException(f"Error uploading image to S3: {e}")
    
    def insertBulk(self, image_paths, image_keys) -> Tuple[List[str], List[str]]:
        success = []
        failure = []
        future_map = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for image_path, image_key in zip(image_paths, image_keys):
                future = executor.submit(self.insert, image_path, image_key)
                future_map[future] = image_key

        for future, image_key in future_map.items():
            try:
                _ = future.result() # This will raise an exception if self.insert() throws exception
                success.append(image_key)
            except Exception as e:
                print(e)
                failure.append(image_key)

        return success, failure

    def remove(self, image_key: str):
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=image_key)
        except Exception as e:
            AdapterException(f"Error deleting image from S3: {e}")


    def insertQueue(self, message: str, message_group_id: str = "default"):
        self.sqs_client.send_message(
            QueueUrl=os.getenv('PUSH_QUEUE_URL'),
            MessageBody=message,
            MessageGroupId=message_group_id
        )