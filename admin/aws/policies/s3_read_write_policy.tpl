{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListBucket"
            ],
            "Resource": [
                "${bucket_arn}"
            ],
            "Condition": {
                "StringLike": {
                    "s3:prefix": [
                        "albums/$${aws:username}/*",
                        "albums/Shared/*"
                    ]
                }
            }
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject"
            ],
            "Resource": [
                "${bucket_arn}/albums/$${aws:username}/*",
                "${bucket_arn}/albums/Shared/*"
            ]
        }
    ]
}