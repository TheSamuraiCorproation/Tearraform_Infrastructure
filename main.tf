provider "aws" {
  region = var.aws_region
}

data "aws_s3_object" "payload" {
  bucket = var.s3_payload_bucket
  key    = var.s3_payload_key
}

locals {
  payload = jsondecode(data.aws_s3_object.payload.body)
}

module "ec2_instances" {
  source = "./modules/ec2"
  for_each = local.payload.instances

  name          = each.value.name
  ami           = each.value.ami
  instance_type = each.value.instance_type
  user_data     = each.value.user_data
}
