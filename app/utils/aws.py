import boto3
from botocore.config import Config
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session
import requests

### AWS Session Utils
def get_aws_autorefresh_session(aws_role_arn, session_name):
    session_credentials = RefreshableCredentials.create_from_metadata(
        metadata = _get_aws_credentials(aws_role_arn, session_name),
        refresh_using = lambda: _get_aws_credentials(aws_role_arn, session_name),
        method = 'sts-assume-role'
    )

    session = get_session()
    session._credentials = session_credentials
    autorefresh_session = boto3.Session(botocore_session=session)

    return autorefresh_session, session_credentials

def _get_aws_credentials(aws_role_arn, session_name):
        sts_client = boto3.client(
            'sts',
            config=Config(
                connect_timeout=2,
                read_timeout=2,
                retries={
                    'total_max_attempts': 1,  # Don't retry
                }
            )
        )
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

def ping(url: str):
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code != 200 or resp.text != "healthy":
            print(f"Unexpected SQS ping response: {resp.status_code} {resp.text}")
            return False
    except Exception as e:
        print(f"Error pinging {url}")
        return False
    return True