resource "aws_lambda_event_source_mapping" "event_queue_trigger" {
  event_source_arn = aws_sqs_queue.event_queue.arn
  function_name    = aws_lambda_function.event_lambda.arn
}

resource "aws_dynamodb_table" "event_table" {
    name = "${local.app_name}-event-table"
    hash_key = "id"
    range_key = "timestamp"
    read_capacity  = 20
    write_capacity = 20

    attribute {
        name = "id"
        type = "S"
    }

    attribute {
        name = "timestamp"
        type = "N"
    }
}