from typing import List, Tuple
import boto3
import os
import concurrent.futures
import time
import functools

from utils import get_aws_autorefresh_session
from cloud_adapters.adapter import Adapter
from cloud_adapters.exceptions import AdapterException

def retry(max_retries=3, exceptions=(Exception,)):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries:
                        raise
                    delay = 2 ** (attempt - 1)
                    print(f"Retry {attempt} failed with {e}, retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
        return wrapper
    return decorator

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

    @retry()
    def get(self, image_key: str) -> bytes:
        try:
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=image_key)
            return obj['Body'].read()
        except Exception as e:
            AdapterException(f"Error getting image from S3: {e}")

    @retry()
    def insert(self, image_path: str, image_key: str):
        try:
            self.s3_client.upload_file(Bucket=self.bucket_name, Filename=image_path, Key=image_key)
        except Exception as e:
            raise AdapterException(f"Error uploading image to S3: {e}")

    @retry()
    def move(self, src_key: str, dest_key: str):
        try:
            response = self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': src_key},
                Key=dest_key
            )
            print(response)
            self.delete(src_key)
        except Exception as e:
            raise AdapterException(f"Error moving image in S3: {e}")

    @retry()
    def delete(self, image_key: str):
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=image_key)
        except Exception as e:
            AdapterException(f"Error deleting image from S3: {e}")

    def insert_bulk(self, image_paths, image_keys) -> Tuple[List[str], List[str]]:
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

    def move_bulk(self, image_key_pairs: List[Tuple[str, str]]) -> Tuple[List[str], List[str]]:
        success = []
        failure = []
        future_map = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for src_key, dest_key in image_key_pairs:
                future = executor.submit(self.move, src_key, dest_key)
                future_map[future] = (src_key, dest_key)

        for future, key_pair in future_map.items():
            try:
                _ = future.result() # This will raise an exception if self.insert() throws exception
                success.append(key_pair)
            except Exception as e:
                print(e)
                failure.append(key_pair)

        return success, failure

    @retry()
    def delete_bulk(self, image_keys: List[str]) -> Tuple[List[str], List[str]]:
        resp = self.s3_client.delete_objects(
            Bucket=self.bucket_name,
            Delete={
                'Objects': [{'Key': k} for k in image_keys]
            } 
        )
        success = [item['Key'] for item in resp.get('Deleted', [])]
        failure = [item['Key'] for item in resp.get('Errors', [])]
        return success, failure

    @retry()
    def insert_queue(self, message: str, message_group_id: str = "default"):
        try:
            self.sqs_client.send_message(
                QueueUrl=os.getenv('PUSH_QUEUE_URL'),
                MessageBody=message,
                MessageGroupId=message_group_id
            )
        except Exception as e:
            raise AdapterException(f"Error sending message to SQS: {e}")