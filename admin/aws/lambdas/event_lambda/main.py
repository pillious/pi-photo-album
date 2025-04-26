import boto3
import time
import uuid
import json
import os
from collections import defaultdict

# Expects the message body to be in the following format:
# {
#     "events": [
#         {
#             "event": "PUT",
#             "path": "albums/album1/image1.jpg",
#         },
#         {
#             "event": "MOVE",
#             "path": "albums/album1/image1.jpg",
#             "newPath": "albums/album1/image2.jpg"
#         },
#         {
#             "event": "DELETE",
#             "path": "albums/album1/image1.jpg"
#         },
#         ...
#     ],
#     "sender: "username"
# }

# Expected Env Vars:
# - SNS_TOPIC_ARN: The ARN of the SNS topic to publish to

def lambda_handler(event, context):
    try:
        if 'Records' not in event:
            raise ValueError('No records')

        sns = boto3.client('sns')

        for message in event['Records']:
            payload = json.loads(message['body'])
            events_by_group_id = defaultdict(list)
            if 'events' in payload:
                for event in payload['events']:
                    message_group_id, message = process_event(event)
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

    message_group_id = get_message_group_id(event['path'])
    return message_group_id, message

def get_message_group_id(path: str):
    if path.startswith('albums/'):
        path = path[len('albums/'):]
    return path.split('/')[0]

def publish(sns_client, message: str, message_group_id: str, message_attributes):
    print(message, message_group_id, message_attributes)
    sns_client.publish(
        TopicArn=os.environ['SNS_TOPIC_ARN'], 
        Message=message, 
        MessageGroupId=message_group_id,
        MessageAttributes=message_attributes)