resource "aws_s3_bucket" "photo_bucket" {
  bucket = "${local.app_name}-s3"

  tags = {
    Name        = "pi-photo-album-s3"
    Environment = "Production"
  }
}

# Policy for accessing S3 bucket
resource "aws_iam_policy" "photo_bucket_policy" {
  name = "${local.app_name}-s3-policy"
  policy = templatefile(
    "policies/s3_read_write_policy.tpl",
    { bucket_arn = aws_s3_bucket.photo_bucket.arn }
  )
}