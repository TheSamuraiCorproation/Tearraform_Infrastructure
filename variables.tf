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
  default     = "https://9216d38c2a3f.ngrok-free.app"
}

variable "subnet_id" {
  description = "Subnet ID for the EC2 instances"
  type        = string
}
