import boto3
import time
import uuid
import json
import os
from collections import defaultdict


def lambda_handler(event, context):
    """
    AWS Lambda function to process events from SQS and publish them to SNS.
    
    The events are batched based on file path prefixes before published to an SNS topic.

    Expected message body format:
    ```
    {
        "events": [
            {
                "event": "PUT",
                "path": "albums/album1/image1.jpg",
            },
            {
                "event": "MOVE",
                "path": "albums/album1/image1.jpg",
                "newPath": "albums/album1/image2.jpg"
            },
            {
                "event": "DELETE",
                "path": "albums/album1/image1.jpg"
            },
            ...
        ],
        "sender: "username"
    }
    ```

    Expected Env Vars:
     - SNS_TOPIC_ARN: The ARN of the SNS topic to publish to
    """
    try:
        if 'Records' not in event:
            raise ValueError('No records')

        sns = boto3.client('sns')

        for message in event['Records']:
            payload = json.loads(message['body'])
            events_by_group_id = defaultdict(list)
            if 'events' in payload:
                for event in payload['events']:
                    message = process_event(event)
                    message_group_id = get_message_group_id(event)
                    events_by_group_id[message_group_id].append(message)
                for message_group_id, events in events_by_group_id.items():
                    message_attributes = {
                        'messageGroupId': {
                            'DataType': 'String',
                            'StringValue': message_group_id
                        },
                        'sender': {
                            'DataType': 'String',
                            'StringValue': payload['sender']
                        }
                    }
                    publish(sns, json.dumps({'events': events}), message_group_id, message_attributes)
    except (ValueError, json.JSONDecodeError) as e:
        print('Error: ', e)


def process_event(event):
    """
    Process the event to create a message for SNS.
    """
    if 'event' not in event or 'path' not in event:
        raise ValueError(f'Invalid payload: {event}')
    if 'event' == 'MOVE' and 'newPath' not in event:
        raise ValueError(f'Invalid payload: {event}')
    id = str(uuid.uuid4())
    message = {
        'event': event['event'], 
        'path': event['path'], 
        'timestamp': round(time.time()), 
        'id': id
    }
    if 'newPath' in event:
        message['newPath'] = event['newPath']

    return message

def get_message_group_id(event):
    """
    Get the message group ID is based on the path prefix.
    
    The only exception is for a MOVE event, when a file is moved from a private folder to a shared folder.
    Then, the new path is used to determine the group ID.
    """
    if 'newPath' in event:
        new_path_prefix = get_path_prefix(event['newPath'])
        if new_path_prefix == 'Shared':
            return new_path_prefix
    return get_path_prefix(event['path'])

def get_path_prefix(path: str):
    """
    Strips the "albums/" prefix (if it exists) and returns the first part of the path.
    """
    if path.startswith('albums/'):
        path = path[len('albums/'):]
    return path.split('/')[0]

def publish(sns_client, message: str, message_group_id: str, message_attributes):
    """
    Publish a message to the SNS topic.
    """
    sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'], 
        Message=message, 
        MessageGroupId=message_group_id,
        MessageAttributes=message_attributes)