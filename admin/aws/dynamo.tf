# resource "aws_dynamodb_table" "event_table" {
#     name = "${local.app_name}-event-table"
#     hash_key = "id"
#     range_key = "timestamp"
#     read_capacity  = 20
#     write_capacity = 20

#     attribute {
#         name = "id"
#         type = "S"
#     }

#     attribute {
#         name = "timestamp"
#         type = "N"
#     }
# }