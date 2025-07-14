provider "aws" {
  region = var.aws_region
}

locals {
  ec2_instances = jsondecode(file("${path.module}/payloads/sample.json")).instances
}

module "ec2" {
  source   = "./modules/ec2"
  for_each = local.ec2_instances

  name           = each.value.name
  ami            = each.value.ami
  instance_type  = each.value.instance_type
  user_data      = each.value.user_data
}

