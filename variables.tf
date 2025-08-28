variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "eu-central-1"
}

variable "s3_payload_bucket" {
  description = "S3 bucket containing the payload"
  type        = string
}

variable "s3_payload_key" {
  description = "S3 key for the payload file"
  type        = string
}

variable "jenkins_url" {
  description = "URL of the Jenkins server"
  type        = string
  default     = "https://4585943c559d.ngrok-free.app"
}


