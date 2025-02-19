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
                        "$${aws:username}/*",
                        "shared/*"
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
                "${bucket_arn}/$${aws:username}/*",
                "${bucket_arn}/shared/*"
            ]
        }
    ]
}