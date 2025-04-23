resource "aws_s3_bucket" "photo_bucket" {
  bucket = "${local.app_name}-s3"

  tags = {
    Name        = "pi-photo-album-s3"
    Environment = "Production"
  }
}