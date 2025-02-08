# Create IAM user
resource "aws_iam_user" "pi_photo_album_user" {
  for_each = toset(local.user_ids)
  name     = each.key
}

# Create access key ID and secret key 
resource "aws_iam_access_key" "user_access_key" {
  for_each = toset(local.user_ids)
  user     = aws_iam_user.pi_photo_album_user[each.key].name
}

# Store the access key ID and secret key in SSM Parameter Store
resource "aws_ssm_parameter" "user_access_key" {
    for_each = toset(local.user_ids)
    name     = "/${local.app_name}/${local.user_id_to_name[each.key]}/access-key"
    type = "SecureString"
    value = aws_iam_access_key.user_access_key[each.key].id
}

resource "aws_ssm_parameter" "user_secret_key" {
    for_each = toset(local.user_ids)
    name     = "/${local.app_name}/${local.user_id_to_name[each.key]}/secret-key"
    type = "SecureString"
    value = aws_iam_access_key.user_access_key[each.key].secret
}

# Create IAM group
resource "aws_iam_group" "editor" {
  name = "${local.app_name}-group"
}

resource "aws_iam_policy_attachment" "editor" {
    name = "editor-attachment"
    groups = [aws_iam_group.editor.name]
    policy_arn = aws_iam_policy.photos_s3_policy.arn
}

resource "aws_iam_user_group_membership" "editor" {
  for_each = toset(local.user_ids)
  user     = aws_iam_user.pi_photo_album_user[each.key].name
  groups   = [aws_iam_group.editor.name]
}