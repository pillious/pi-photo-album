import boto3
import os

from cloud_adapters.adapter import Adapter
from cloud_adapters.exceptions import AdapterException

class S3Adapter(Adapter):
    def __init__(self, bucket_name: str):
        self.s3_client = boto3.client(
            's3', 
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS'),
        )
        self.bucket_name = bucket_name

    def get_album(self, album_path):
        pass

    def get(self, image_key: str) -> bytes:
        try:
            obj = self.s3_client.get_object(Bucket=self.bucket_name, Key=image_key)
            return obj['Body'].read()
        except Exception as e:
            AdapterException(f"Error getting image from S3: {e}")

    def insert(self, image_path: str, image_key: str):
        try:
            return self.s3_client.upload_file(Bucket=self.bucket_name, Filename=image_path, Key=image_key)
        except Exception as e:
            AdapterException(f"Error uploading image to S3: {e}")
    
    def remove(self, image_key: str):
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=image_key)
        except Exception as e:
            AdapterException(f"Error deleting image from S3: {e}")