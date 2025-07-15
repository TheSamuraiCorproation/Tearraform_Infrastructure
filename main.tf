provider "aws" {
  region = var.aws_region
}

variable "payload_s3_key" {
  description = "The S3 key of the payload JSON file"
  type        = string
}

data "aws_s3_object" "payload" {
  bucket = "thesamuraibucket"
  key    = var.payload_s3_key
}

locals {
  payload_content = jsondecode(data.aws_s3_object.payload.body)
}

module "ec2_instances" {
  source = "./modules/ec2"
  for_each = local.payload_content.instances

  name          = each.value.name
  ami           = each.value.ami
  instance_type = each.value.instance_type
  user_data     = each.value.user_data
}
