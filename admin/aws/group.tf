resource "aws_iam_group" "editor_group" {
  name = "${local.app_name}-group"
}

resource "aws_iam_policy_attachment" "editor_policy_attachment" {
  name       = "${local.app_name}-editor-attachment"
  groups     = [aws_iam_group.editor_group.name]
  policy_arn = aws_iam_policy.photo_bucket_policy.arn
}

resource "aws_iam_user_group_membership" "editor_group_membership" {
  for_each = toset(local.user_ids)
  user     = aws_iam_user.pi_photo_album_user[each.key].name
  groups   = [aws_iam_group.editor_group.name]
}

resource "aws_iam_policy_attachment" "editor_assume_role_policy_attachment" {
  name       = "${local.app_name}-editor-assume-role-policy-attachment"
  groups     = [aws_iam_group.editor_group.name]
  policy_arn = aws_iam_policy.editor_assume_role_policy.arn
}

resource "aws_iam_policy" "editor_assume_role_policy" {
  name   = "${local.app_name}-editor-assume-role-policy"
  policy = templatefile("policies/assume_role_policy.tpl", { role_arn = aws_iam_role.push_event_role.arn })
}

resource "aws_iam_role" "push_event_role" {
  name               = "${local.app_name}-push-event-role"
  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": [
          "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "push_event_policy" {
  name   = "${local.app_name}-push-event-policy"
  policy = templatefile("policies/push_event_policy.tpl", { queue_arn = aws_sqs_queue.event_queue.arn })
}

resource "aws_iam_policy_attachment" "assume_push_event_policy_attachment" {
  name       = "${local.app_name}-assume-push-event-policy-attachment"
  roles      = [aws_iam_role.push_event_role.name]
  policy_arn = aws_iam_policy.push_event_policy.arn
}