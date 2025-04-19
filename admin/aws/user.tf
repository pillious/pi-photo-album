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
  type     = "SecureString"
  value    = aws_iam_access_key.user_access_key[each.key].id
}

resource "aws_ssm_parameter" "user_secret_key" {
  for_each = toset(local.user_ids)
  name     = "/${local.app_name}/${local.user_id_to_name[each.key]}/secret-key"
  type     = "SecureString"
  value    = aws_iam_access_key.user_access_key[each.key].secret
}

resource "aws_iam_policy" "read_receive_event_queue_policy" {
  for_each = toset(local.user_ids)
  name     = "${each.key}-read-receive-event-queue-policy"
  policy   = templatefile("policies/read_receive_event_queue_policy.tpl", { queue_arn = aws_sqs_queue.receive_event_queue[each.key].arn })
}

resource "aws_iam_user_policy_attachment" "read_receive_event_queue_policy_attachment" {
  for_each   = toset(local.user_ids)
  user       = aws_iam_user.pi_photo_album_user[each.key].name
  policy_arn = aws_iam_policy.read_receive_event_queue_policy[each.key].arn
}