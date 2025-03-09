from typing import List, Tuple
import boto3
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
import os

import concurrent.futures

from cloud_adapters.adapter import Adapter
from cloud_adapters.exceptions import AdapterException

class S3Adapter(Adapter):
    def __init__(self, bucket_name: str):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client(
            's3', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
        )

        autorefresh_session, _ = self._get_aws_autorefresh_session(os.getenv('PUSH_QUEUE_ROLE'), "push-queue-session")
        self.sqs_client = autorefresh_session.client('sqs')

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
            QueueUrl=os.getenv('QUEUE_URL'),
            MessageBody=message,
            MessageGroupId=message_group_id
        )

    def _get_aws_credentials(self, aws_role_arn, session_name):
        sts_client = boto3.client('sts')
        assumed_role_object = sts_client.assume_role(
            RoleArn = aws_role_arn,
            RoleSessionName = session_name,
            DurationSeconds = 900
        )
        return {
            'access_key': assumed_role_object['Credentials']['AccessKeyId'],
            'secret_key': assumed_role_object['Credentials']['SecretAccessKey'],
            'token': assumed_role_object['Credentials']['SessionToken'],
            'expiry_time': assumed_role_object['Credentials']['Expiration'].isoformat()
        }

    def _get_aws_autorefresh_session(self, aws_role_arn, session_name):
        session_credentials = RefreshableCredentials.create_from_metadata(
            metadata = self._get_aws_credentials(aws_role_arn, session_name),
            refresh_using = lambda: self._get_aws_credentials(aws_role_arn, session_name),
            method = 'sts-assume-role'
        )

        session = get_session()
        session._credentials = session_credentials
        autorefresh_session = boto3.Session(botocore_session=session)

        return autorefresh_session, session_credentials