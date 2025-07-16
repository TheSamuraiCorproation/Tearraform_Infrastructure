variable "jenkins_token" {
  description = "Jenkins authentication token"
  type        = string
  sensitive   = true
}

variable "jenkins_user" {
  description = "Jenkins username for API authentication"
  type        = string
  sensitive   = true
}

variable "jenkins_api_token" {
  description = "Jenkins API token for authentication"
  type        = string
  sensitive   = true
}

resource "aws_iam_role" "lambda_role" {
  name = "s3-to-jenkins-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_logging"
  role = aws_iam_role.lambda_role.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

resource "aws_lambda_function" "forwarder" {
  filename         = "lambda.zip"
  function_name    = "s3-to-jenkins-forwarder"
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.9"
  role             = aws_iam_role.lambda_role.arn
  source_code_hash = filebase64sha256("lambda.zip")
  description      = "Triggers Jenkins pipeline on S3 JSON upload"
  timeout          = 60

  environment {
    variables = {
      JENKINS_URL       = "http://197.1.206.75:8080"
      JOB_NAME          = "terraform-deploy"
      JENKINS_TOKEN     = var.jenkins_token
      JENKINS_USER      = var.jenkins_user
      JENKINS_API_TOKEN = var.jenkins_api_token
    }
  }
}

resource "aws_lambda_permission" "allow_s3" {
  statement_id  = "AllowS3Invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.forwarder.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::thesamuraibucket"
}

resource "aws_s3_bucket_notification" "notify_lambda" {
  bucket = "thesamuraibucket"

  lambda_function {
    lambda_function_arn = aws_lambda_function.forwarder.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3]
}
