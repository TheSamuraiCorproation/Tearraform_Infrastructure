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

module "ec2" {
  source   = "./modules/ec2"
  instances = local.payload.instances
}

output "ec2_public_ips" {
  value = module.ec2_instances.public_ips
}
