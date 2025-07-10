from typing import List, Tuple
import boto3
import botocore
import os
import concurrent.futures
import time
import functools

import botocore.config
import botocore.exceptions

from app.utils.aws import get_aws_autorefresh_session
from app.cloud_adapters.adapter import Adapter
from app.cloud_adapters.exceptions import AdapterException

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

        self.s3_client = self._create_s3_client()
        self.sqs_client = self._create_sqs_client()

    def _create_s3_client(self):
        return boto3.client(
            's3', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION'),
            config=botocore.config.Config(
                connect_timeout=2,
                read_timeout=2,
                retries={'total_max_attempts': 1} # Don't retry
            )
        )

    def _create_sqs_client(self):
        try:
            autorefresh_session, _ = get_aws_autorefresh_session(os.getenv('PUSH_QUEUE_ROLE'), "push-queue-session")
            return autorefresh_session.client('sqs', region_name=os.getenv('AWS_REGION'))
        except botocore.exceptions.EndpointConnectionError:
            return None

    def get_album(self, album_path):
        pass

    @retry()
    def list_album(self, album_path: str) -> List[str]:
        paginator = self.s3_client.get_paginator('list_objects_v2')
        page_iterator = paginator.paginate(
            Bucket=self.bucket_name,
            Prefix=album_path
        )
        image_keys = []
        # Each page is limited to 1000 objects
        for page in page_iterator:
            image_keys.extend([obj['Key'] for obj in page.get('Contents', [])])

        return image_keys

    @retry()
    def get(self, image_key: str) -> bytes:
        try:
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=image_key)
            return obj['Body'].read()
        except Exception as e:
            AdapterException(f"Error getting image from S3: {e}")
        return bytes()

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
            self.delete(src_key)
        except Exception as e:
            raise AdapterException(f"Error moving image in S3: {e}")

    @retry()
    def delete(self, image_key: str):
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=image_key)
        except Exception as e:
            AdapterException(f"Error deleting image from S3: {e}")

    def get_bulk(self, image_paths: List[str], image_keys: List[str]) -> Tuple[List[str], List[str]]:
        success = []
        failure = []
        future_map = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for image_path, image_key in zip(image_paths, image_keys):
                future = executor.submit(self.get, image_key)
                future_map[future] = (image_path, image_key)

            for future in concurrent.futures.as_completed(future_map):
                image_path, image_key = future_map[future]
                try:
                    image_bytes: bytes = future.result()
                    os.makedirs(os.path.dirname(image_path), exist_ok=True)
                    with open(image_path, "wb") as f:
                        f.write(image_bytes)
                    success.append(image_key)
                except Exception as e:
                    print(e)
                    failure.append(image_key)

        return success, failure

    def insert_bulk(self, image_paths: List[str], image_keys: List[str]) -> Tuple[List[str], List[str]]:
        success = []
        failure = []
        future_map = {}
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for image_path, image_key in zip(image_paths, image_keys):
                future = executor.submit(self.insert, image_path, image_key)
                future_map[future] = image_key

            for future in concurrent.futures.as_completed(future_map):
                image_key = future_map[future]
                try:
                    _ = future.result()
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

            for future in concurrent.futures.as_completed(future_map):
                key_pair = future_map[future]
                try:
                    _ = future.result()
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
            if not self.sqs_client:
                self._create_sqs_client()
            if self.sqs_client:
                self.sqs_client.send_message(
                    QueueUrl=os.getenv('PUSH_QUEUE_URL'),
                    MessageBody=message,
                    MessageGroupId=message_group_id
                )
        except Exception as e:
            raise AdapterException(f"Error sending message to SQS: {e}")