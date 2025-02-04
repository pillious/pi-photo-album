data "aws_caller_identity" "current" {}

locals {
  region     = "us-east-1"
  app_name   = "pi-photo-album"
  user_names = ["alee1246"]

  user_ids   = [for name in toset(local.user_names) : "${local.app_name}-user-${name}"]
}

provider "aws" {
  region = local.region
}