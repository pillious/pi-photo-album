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

# Store the access key ID and secret key in Secrets Manager
resource "aws_secretsmanager_secret" "user_access_keys" {
  for_each = toset(local.user_ids)
  name     = "${each.key}-access-keys"
}

resource "aws_secretsmanager_secret_version" "user_access_key" {
  for_each  = toset(local.user_ids)
  secret_id = aws_secretsmanager_secret.user_access_keys[each.key].id
  secret_string = jsonencode({
    access_key = aws_iam_access_key.user_access_key[each.key].id,
    secret_key = aws_iam_access_key.user_access_key[each.key].secret
  })
}

# Create IAM group
resource "aws_iam_group" "editor" {
  name = "${local.app_name}-group"
}

resource "aws_iam_policy" "editor" {
  name = "${local.app_name}-assume-role-policy"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = "sts:AssumeRole"
        Resource = aws_iam_role.photos.arn
      }
    ]
  })
}

resource "aws_iam_policy_attachment" "assume_role_attach" {
  name       = "assume-role-attachment"
  groups     = [aws_iam_group.editor.name]
  policy_arn = aws_iam_policy.editor.arn
}

resource "aws_iam_user_group_membership" "editor" {
  for_each = toset(local.user_ids)
  user     = aws_iam_user.pi_photo_album_user[each.key].name
  groups   = [aws_iam_group.editor.name]
}