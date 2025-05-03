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
                        "albums/${username}/*",
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
                "s3:DeleteObject",
                "s3:CopyObject"
            ],
            "Resource": [
                "${bucket_arn}/albums/${username}/*",
                "${bucket_arn}/albums/Shared/*"
            ]
        }
    ]
}