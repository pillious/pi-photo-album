{
    "Version": "2012-10-17",
    "Statement": [
      {
        "Effect": "Allow",
        "Action": [
          "sqs:SendMessage"
        ],
        "Principal": {
            "AWS": [
                "${role_arn}"
            ]
        },
        "Resource": "${queue_arn}"
      }
    ]
}