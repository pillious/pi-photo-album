import boto3
import time
import uuid
import json
import os

def lambda_handler(event, context):
    try:
        if 'Records' not in event:
            raise ValueError("No records")

        dynamodb = boto3.client('dynamodb')
        sns = boto3.client('sns')
        for message in event['Records']:
            payload = json.loads(message['body'])
            if 'event' not in payload or 'path' not in payload:
                raise ValueError(f"Invalid payload: {payload}")
            if 'event' == 'MOVE' and 'newPath' not in payload:
                raise ValueError(f"Invalid payload: {payload}")
            id = str(uuid.uuid4())
            # TODO: remove the add to database.
            add_to_db(dynamodb, id, payload['event'], payload['path'])
            message_group_id = get_message_group_id(payload['path'])
            message = {
                "event": payload['event'], 
                "path": payload['path'], 
                "timestamp": round(time.time()), 
                "messageGroupId": message_group_id,
                "id": id
            }
            if 'newPath' in payload:
                message['newPath'] = payload['newPath']
            publish_event(sns, json.dumps(message), message_group_id)
    except (ValueError, json.JSONDecodeError) as e:
        print("Error: ", e)

# TODO: remove.
def add_to_db(dynamo_client, id: str, event: str, path: str):
    dynamo_client.put_item(TableName=os.environ['TABLE_NAME'], Item={
        'id': {'S': id},
        'event': {'S': event},
        'path': {'S': path},
        'timestamp': {'N': str(round(time.time()))}
    })

def publish_event(sns_client, message: str, message_group_id: str):
    print(message, message_group_id)
    # sns_client.publish(TopicArn=os.environ['SNS_TOPIC_ARN'], Message=message, MessageGroupId=message_group_id)

def get_message_group_id(path: str):
    if path.startswith("album/"):
        path = path[len("album/"):]
    return path.split('/')[0]