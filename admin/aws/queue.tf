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
  name                        = "${local.app_name}-event-sns-topic.fifo"
  fifo_topic                  = true
  content_based_deduplication = true
}

resource "aws_sns_topic_subscription" "event_topic_subscription" {
  for_each  = toset(local.user_ids)
  topic_arn = aws_sns_topic.event_topic.arn
  protocol  = "sqs"
  endpoint  = aws_sqs_queue.receive_event_queue[each.key].arn

  filter_policy = jsonencode({
    messageGroupId = [local.user_id_to_name[each.key], "Shared"]
  })
}

# SNS -> SQS#2
resource "aws_sqs_queue" "receive_event_queue" {
  for_each                    = toset(local.user_ids)
  name                        = "${each.key}-receive-event-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

