locals {
  region     = "us-east-1"
  app_name   = "pi-photo-album"
  user_names = ["alee1246"]

  user_ids   = [for name in toset(local.user_names) : "${local.app_name}-user-${name}"]
  user_id_to_name = zipmap(local.user_ids, local.user_names)
}

provider "aws" {
  region = local.region
}

data "aws_caller_identity" "current" {}