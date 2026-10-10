variable "sender_email" {
  type = string
}

variable "recipient_email" {
  type = string
}

data "aws_caller_identity" "current" {}

data "archive_file" "reminder" {
  type        = "zip"
  source_file = "${path.module}/../backend/reminder.py"
  output_path = "${path.module}/reminder.zip"
}

resource "aws_iam_role" "reminder_role" {
  name = "duesoon-reminder-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "reminder_logs" {
  role       = aws_iam_role.reminder_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "reminder_access" {
  name = "duesoon-reminder-access"
  role = aws_iam_role.reminder_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["dynamodb:Scan", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.assignments.arn
      },
      {
        Effect   = "Allow"
        Action   = "ses:SendEmail"
        Resource = "arn:aws:ses:us-east-1:${data.aws_caller_identity.current.account_id}:identity/*"
      }
    ]
  })
}

resource "aws_lambda_function" "reminders" {
  function_name    = "duesoon-reminders"
  role             = aws_iam_role.reminder_role.arn
  runtime          = "python3.12"
  handler          = "reminder.lambda_handler"
  filename         = data.archive_file.reminder.output_path
  source_code_hash = data.archive_file.reminder.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.assignments.name
      SENDER     = var.sender_email
      RECIPIENT  = var.recipient_email
    }
  }
}