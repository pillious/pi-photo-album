resource "aws_s3_bucket" "photos" {
  bucket = "${local.app_name}-s3"

  tags = {
    Name        = "pi-photo-album-s3"
    Environment = "Production"
  }
}

# Role for accessing S3 bucket
resource "aws_iam_role" "photos" {
  name               = "${local.app_name}-role"
  assume_role_policy = file("policies/assume_role.json")
}

resource "aws_iam_policy" "photos_s3_policy" {
  name = "${local.app_name}-s3-policy"
  policy = templatefile(
    "policies/s3_read_write.tpl",
    { bucket_arn = aws_s3_bucket.photos.arn }
  )
}

resource "aws_iam_policy_attachment" "photos_s3_attach" {
  name       = "photos-s3-attach"
  roles      = [aws_iam_role.photos.name]
  policy_arn = aws_iam_policy.photos_s3_policy.arn
}