# Client -> SQS#1
resource "aws_sqs_queue" "event_queue" {
  name                        = "${local.app_name}-event-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

resource "aws_sqs_queue_policy" "event_queue_policy" {
  queue_url = aws_sqs_queue.event_queue.id
  policy = templatefile(
    "policies/event_queue_policy.tpl",
    {
      role_arn  = aws_iam_role.push_event_role.arn,
      queue_arn = aws_sqs_queue.event_queue.arn
    }
  )
}

# Lambda -> SNS
resource "aws_sns_topic" "event_topic" {
  name                             = "${local.app_name}-event-sns-topic.fifo"
  fifo_topic                       = true
  content_based_deduplication      = true
  sqs_success_feedback_role_arn    = aws_iam_role.event_topic_log_role.arn
  sqs_failure_feedback_role_arn    = aws_iam_role.event_topic_log_role.arn
  sqs_success_feedback_sample_rate = 100

  depends_on = [aws_cloudwatch_log_group.event_topic_log_group]
}

resource "aws_sns_topic_subscription" "event_topic_subscription" {
  for_each  = toset(local.user_ids)
  topic_arn = aws_sns_topic.event_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.receive_event_queue[each.key].arn

  # Only accepts events to "Shared" folder that were not emitted from the current user.
  filter_policy = jsonencode({
    sender         = [{ "anything-but" = [local.user_id_to_name[each.key]] }]
    messageGroupId = ["Shared"]
  })
}

resource "aws_iam_role" "event_topic_log_role" {
  name               = "${local.app_name}-event-topic-log-role"
  assume_role_policy = templatefile("policies/service_assume_role_policy.tpl", { service = "sns.amazonaws.com" })
}

resource "aws_cloudwatch_log_group" "event_topic_log_group" {
  name              = "/aws/sns/${local.app_name}-event-sns-topic.fifo"
  retention_in_days = 14
}

# https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicExecutionRole.html
resource "aws_iam_policy_attachment" "event_topic_logs_policy_attachment" {
  name       = "${local.app_name}-event-lambda-logs-policy-attachment"
  roles      = [aws_iam_role.event_topic_log_role.name]
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# SNS -> SQS#2
resource "aws_sqs_queue" "receive_event_queue" {
  for_each                    = toset(local.user_ids)
  name                        = "${each.key}-receive-event-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

resource "aws_sqs_queue_policy" "receive_event_queue_policy" {
  for_each  = toset(local.user_ids)
  queue_url = aws_sqs_queue.receive_event_queue[each.key].id
  policy = templatefile(
    "policies/receive_event_queue_policy.tpl",
    {
      topic_arn = aws_sns_topic.event_topic.arn,
      queue_arn = aws_sqs_queue.receive_event_queue[each.key].arn
      user_arn  = aws_iam_user.pi_photo_album_user[each.key].arn
    }
  )
}

