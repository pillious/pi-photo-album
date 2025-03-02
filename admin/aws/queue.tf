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

### Event Queue Lambda Trigger ###
resource "aws_iam_role" "event_lambda_role" {
  name               = "${local.app_name}-event-lambda-role"
  assume_role_policy = file("policies/lambda_assume_role_policy.json")
}

resource "aws_iam_policy" "lambda_read_queue_policy" {
    name   = "${local.app_name}-lambda-read-queue-policy"
    policy = templatefile("policies/read_queue_policy.tpl", { queue_arn = aws_sqs_queue.event_queue.arn })
}

resource "aws_iam_policy_attachment" "lambda_read_queue_policy_attachment" {
    name       = "${local.app_name}-lambda-read-queue-policy-attachment"
    policy_arn = aws_iam_policy.lambda_read_queue_policy.arn
    roles      = [aws_iam_role.event_lambda_role.name]
}

resource "aws_lambda_function" "event_lambda" {
    filename      = data.archive_file.event_lambda_zip.output_path
    function_name = "${local.app_name}-event-lambda"
    role          = aws_iam_role.event_lambda_role.arn
    handler       = "main.lambda_handler"
    runtime       = "python3.13"
    source_code_hash = data.archive_file.event_lambda_zip.output_base64sha256

    depends_on = [ 
        aws_cloudwatch_log_group.event_lambda_log_group, 
        aws_iam_policy_attachment.lambda_write_table_policy_attachment 
    ]
}

data "archive_file" "event_lambda_zip" {
  type = "zip"
  source_dir = "${path.module}/lambdas/event_lambda/"
  output_path = "${path.module}/tmp/event_lambda.zip"
}

resource "aws_lambda_event_source_mapping" "event_queue_trigger" {
  event_source_arn = aws_sqs_queue.event_queue.arn
  function_name    = aws_lambda_function.event_lambda.arn
}

resource "aws_iam_policy" "lambda_write_table_policy" {
    name   = "${local.app_name}-lambda-write-table-policy"
    policy = templatefile("policies/write_table_policy.tpl", { table_arn = aws_dynamodb_table.event_table.arn })
}

resource "aws_iam_policy_attachment" "lambda_write_table_policy_attachment" {
    name       = "${local.app_name}-lambda-write-table-policy-attachment"
    policy_arn = aws_iam_policy.lambda_write_table_policy.arn
    roles      = [aws_iam_role.event_lambda_role.name]
}

### Lambda Cloudwatch logs ###

resource "aws_cloudwatch_log_group" "event_lambda_log_group" {
  name              = "${local.app_name}-event-lambda-log-group"
  retention_in_days = 14
}

# https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AWSLambdaBasicExecutionRole.html
resource "aws_iam_policy_attachment" "event_lambda_logs_policy_attachment" {
    name = "${local.app_name}-event-lambda-logs-policy-attachment"
    roles = [aws_iam_role.event_lambda_role.name]
    policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

### DynamoDB Table ###

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



# resource "aws_iam_policy" "event_table_policy" {
#     name   = "${local.app_name}-event-table-policy"
#     policy = templatefile("policies/event_table_policy.json")
# }