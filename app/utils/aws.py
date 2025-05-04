import boto3
from botocore.credentials import RefreshableCredentials
from botocore.session import get_session

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