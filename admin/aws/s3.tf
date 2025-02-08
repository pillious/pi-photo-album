resource "aws_s3_bucket" "photos" {
  bucket = "${local.app_name}-s3"

  tags = {
    Name        = "pi-photo-album-s3"
    Environment = "Production"
  }
}

# Policy for accessing S3 bucket
resource "aws_iam_policy" "photos_s3_policy" {
  name = "${local.app_name}-s3-policy"
  policy = templatefile(
    "policies/s3_read_write.tpl",
    { bucket_arn = aws_s3_bucket.photos.arn }
  )
}