import pytest
import os
import boto3
import json
from moto import mock_aws
from pathlib import Path

from app.cloud_clients.aws_client import AWSClient
from app.tests import utils

#####
# Notes:
# - Moto currently doesn't support conditions in IAM policies, so the tests here are limited.
#####

class TestAWSClient:
    @pytest.fixture(scope="function")
    def fs(self):
        return {
            "albums": {
                "test-user": {
                    "photo1.jpg": "",
                    "photo2.jpg": "",
                    "a": {
                        "photo3.jpg": "",
                        "photo4.jpg": ""
                    }
                },
                "other-user": {
                    "photo5.jpg": "",
                    "photo6.jpg": ""
                }
            }
        }

    @pytest.fixture(scope="function")
    def env(self):
        os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
        os.environ["AWS_REGION"] = "us-east-1"
        os.environ["PUSH_QUEUE_URL"] = "https://sqs.us-east-1.amazonaws.com/000000000000/testing-queue.fifo"
        os.environ["PUSH_QUEUE_ROLE"] = "arn:aws:iam::000000000000:role/testing"
        os.environ["S3_BUCKET_NAME"] = "test-bucket"
        os.environ["USERNAME"] = "test-user"

    @pytest.fixture(scope="function")
    def iam(self, env):
        """
        Return a mocked IAM client
        """
        with mock_aws():
            yield boto3.client("iam", region_name=os.getenv("AWS_DEFAULT_REGION"))

    @pytest.fixture(scope="function")
    def s3(self, env):
        """
        Return a mocked S3 client
        """
        with mock_aws():
            yield boto3.client("s3", region_name=os.getenv("AWS_DEFAULT_REGION"))

    @pytest.fixture(scope="function")
    def user_access_key(self, iam):
        """
        Should create a user with attached policy allowing read/write operations on S3.
        """
        username = os.getenv("USERNAME")
        policy_document = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": "s3:ListBucket",
                    "Resource": f"arn:aws:s3:::{os.getenv('S3_BUCKET_NAME')}",
                    "Condition": {"StringLike": {"s3:prefix": [f"albums/{username}/*"]}}},
            ]
        }

        iam.create_user(UserName=username)
        policy_arn = iam.create_policy(
            PolicyName="s3_read_write_policy", PolicyDocument=json.dumps(policy_document)
        )["Policy"]["Arn"]
        iam.attach_user_policy(UserName=username, PolicyArn=policy_arn)

        return iam.create_access_key(UserName=username)["AccessKey"]

    @pytest.fixture(scope="function")
    def aws_credentials(self, user_access_key):
        """Mocked AWS Credentials for moto."""
        os.environ["AWS_ACCESS_KEY_ID"] = user_access_key["AccessKeyId"]
        os.environ["AWS_SECRET_ACCESS_KEY"] = user_access_key["SecretAccessKey"]
        os.environ["AWS_SECURITY_TOKEN"] = "testing"
        os.environ["AWS_SESSION_TOKEN"] = "testing"

    @pytest.fixture(scope="function")
    def aws_client(self, aws_credentials, fs):
        """
        Return an instance of the AWSClient with mocked S3 and SQS clients
        """
        client = AWSClient(bucket_name=os.getenv("S3_BUCKET_NAME", "test-bucket"))
        return client

    @pytest.fixture(scope="function")
    def test_bucket(self, fs, aws_client):
        aws_client.s3_client.create_bucket(Bucket=os.getenv("S3_BUCKET_NAME"))

        for item in utils.dict_fs_to_list(fs):
            aws_client.s3_client.put_object(Bucket=os.getenv("S3_BUCKET_NAME"), Key=item, Body=b"test")

    def test_list_empty_album(self, aws_client, test_bucket):
        results = aws_client.list_album("albums/test-user/ghost")
        assert len(results) == 0

    def test_list_album(self, fs, aws_client, test_bucket):
        results = aws_client.list_album("albums/test-user/")
        assert len(results) == 4
        assert(set(results) == set(utils.dict_fs_to_list(fs, "albums/test-user/")))

    def test_get(self, aws_client, test_bucket):
        result = aws_client.get("albums/test-user/photo1.jpg")
        assert result == b"test"

    def test_get_nonexistent_image(self, aws_client, test_bucket):
        result = aws_client.get("albums/test-user/nonexistent.jpg")
        assert result == b""

    def test_insert(self, aws_client, test_bucket, tmp_path: Path):
        test_image_path = tmp_path / "new_photo.jpg"
        file_content = b"test"
        with open(test_image_path, "wb") as f:
            f.write(file_content)

        aws_client.insert(str(test_image_path), "albums/test-user/new_photo.jpg")
        result = aws_client.get("albums/test-user/new_photo.jpg")
        assert result == file_content

    def test_insert_overwrite(self, aws_client, test_bucket, tmp_path: Path):
        test_image_path = tmp_path / "photo1.jpg"
        file_content = b"test_new"
        with open(test_image_path, "wb") as f:
            f.write(file_content)

        aws_client.insert(str(test_image_path), "albums/test-user/photo1.jpg")
        result = aws_client.get("albums/test-user/photo1.jpg")
        assert result == file_content

    def test_delete(self, aws_client, test_bucket):
        aws_client.delete("albums/test-user/photo1.jpg")
        result = aws_client.get("albums/test-user/photo1.jpg")
        assert result == b""

    def test_delete_nonexistent_image(self, aws_client, test_bucket):
        # Should not raise an error
        aws_client.delete("albums/test-user/nonexistent.jpg")
        result = aws_client.get("albums/test-user/nonexistent.jpg")
        assert result == b""

    def test_move(self, aws_client, test_bucket):
        aws_client.move("albums/test-user/photo1.jpg", "albums/test-user/photo1_renamed.jpg")
        result = aws_client.get("albums/test-user/photo1.jpg")
        assert result == b""
        result = aws_client.get("albums/test-user/photo1_renamed.jpg")
        assert result == b"test"

    def test_move_nonexistent_image(self, aws_client, test_bucket):
        with pytest.raises(Exception):
            aws_client.move("albums/test-user/nonexistent.jpg", "albums/test-user/should_not_exist.jpg")

    # def test_insert_bulk(self, aws_client, test_bucket, tmp_path: Path):
        # test_image_paths = []
        # image_keys = []
        # file_content = b"test_bulk"
        # for i in range(5):
        #     test_image_path = tmp_path / f"bulk_photo_{i}.jpg"
        #     with open(test_image_path, "wb") as f:
        #         f.write(file_content)
        #     test_image_paths.append(str(test_image_path))
        #     image_keys.append(f"albums/test-user/bulk_photo_{i}.jpg")

        # success, failure = aws_client.insert_bulk(test_image_paths, image_keys)
        # assert set(success) == set(image_keys)
        # assert len(failure) == 0

        # for key in image_keys:
        #     result = aws_client.get(key)
        #     assert result == file_content