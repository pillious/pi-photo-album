import boto3
import time
import uuid
import json
import os

def lambda_handler(event, context):
    try:
        if 'Records' not in event:
            raise ValueError("No records")

        sns = boto3.client('sns')
        for message in event['Records']:
            payload = json.loads(message['body'])
            if 'event' not in payload or 'path' not in payload:
                raise ValueError(f"Invalid payload: {payload}")
            if 'event' == 'MOVE' and 'newPath' not in payload:
                raise ValueError(f"Invalid payload: {payload}")
            id = str(uuid.uuid4())
            message_group_id = get_message_group_id(payload['path'])
            message_attributes = {
                'messageGroupId': {
                    'DataType': 'String',
                    'StringValue': message_group_id
                }
            }
            message = {
                "event": payload['event'], 
                "path": payload['path'], 
                "timestamp": round(time.time()), 
                "id": id
            }
            if 'newPath' in payload:
                message['newPath'] = payload['newPath']
            publish_event(sns, json.dumps(message), message_group_id, message_attributes)
    except (ValueError, json.JSONDecodeError) as e:
        print("Error: ", e)

def publish_event(sns_client, message: str, message_group_id: str, message_attributes):
    print(message, message_group_id, message_attributes)
    print(os.environ['SNS_TOPIC_ARN'])
    response = sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'], 
        Message=message, 
        MessageGroupId=message_group_id,
        MessageAttributes=message_attributes)
    print(response)

def get_message_group_id(path: str):
    if path.startswith("albums/"):
        path = path[len("albums/"):]
    return path.split('/')[0]