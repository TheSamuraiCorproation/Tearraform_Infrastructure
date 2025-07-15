variable "aws_region" {
  description = "The AWS region to deploy resources"
  default     = "eu-central-1"
}

variable "s3_payload_bucket" {
  description = "The S3 bucket containing the payload JSON file"
  type        = string
}

variable "s3_payload_key" {
  description = "The S3 key of the payload JSON file"
  type        = string
}
