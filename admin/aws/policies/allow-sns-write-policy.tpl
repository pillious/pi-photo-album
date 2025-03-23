{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "sqs:SendMessage"
        ],
        "Principal": { 
            "Service": "sns.amazonaws.com" 
        },
        "Condition": { 
            "ArnLike": { 
                "aws:SourceArn": "${topic_arn}"
            } 
        },
        "Resource": "${queue_arn}"
      }
    ]
}