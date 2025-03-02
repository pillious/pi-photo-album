import boto3
import time
import uuid

def lambda_handler(event, context):
    dynamodb = boto3.client('dynamodb')

    dynamodb.put_item(TableName='pi-photo-album-event-table', Item={
        'id': {'S': str(uuid.uuid4())},
        'event': {'S': 'PUT'},
        'path': {'S': 'my/path/to/somewhere'},
        'timestamp': {'N': str(time.time())}
    })

    for message in event['Records']:
        process_message(message)
    print("done")

def process_message(message):
    try:
        print(f"Processed message {message['body']}")
        # TODO: Do interesting work based on the new message
    except Exception as err:
        print("An error occurred")
        raise err