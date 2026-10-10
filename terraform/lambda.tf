variable "passcode" {
  type      = string
  sensitive = true
}

data "archive_file" "submit" {
  type        = "zip"
  source_file = "${path.module}/../backend/submit.py"
  output_path = "${path.module}/submit.zip"
}

resource "aws_iam_role" "submit_role" {
  name = "duesoon-submit-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "submit_logs" {
  role       = aws_iam_role.submit_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "submit_write" {
  name = "duesoon-write-assignments"
  role = aws_iam_role.submit_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "dynamodb:PutItem"
      Resource = aws_dynamodb_table.assignments.arn
    }]
  })
}

resource "aws_lambda_function" "submit" {
  function_name    = "duesoon-submit"
  role             = aws_iam_role.submit_role.arn
  runtime          = "python3.12"
  handler          = "submit.lambda_handler"
  filename         = data.archive_file.submit.output_path
  source_code_hash = data.archive_file.submit.output_base64sha256
  timeout          = 10

  environment {
    variables = {
      TABLE_NAME = aws_dynamodb_table.assignments.name
      PASSCODE   = var.passcode
    }
  }
}

resource "aws_lambda_function_url" "submit" {
  function_name      = aws_lambda_function.submit.function_name
  authorization_type = "NONE"
}

resource "aws_lambda_permission" "url_public" {
  statement_id           = "FunctionURLAllowPublicAccess"
  action                 = "lambda:InvokeFunctionUrl"
  function_name          = aws_lambda_function.submit.function_name
  principal              = "*"
  function_url_auth_type = "NONE"
}

resource "aws_lambda_permission" "url_invoke" {
  statement_id             = "FunctionURLInvokeAllowPublicAccess"
  action                   = "lambda:InvokeFunction"
  function_name            = aws_lambda_function.submit.function_name
  principal                = "*"
  invoked_via_function_url = true
}

output "submit_url" {
  value = aws_lambda_function_url.submit.function_url
}