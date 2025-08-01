# Generate an RSA private key
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

# Create an AWS key pair using the generated public key
resource "aws_key_pair" "ec2_key_pair" {
  key_name   = "client-access-key"
  public_key = tls_private_key.ec2_key.public_key_openssh
}

# Output the private key for Jenkins to use
output "private_key_pem" {
  value     = tls_private_key.ec2_key.private_key_pem
  sensitive = true
}

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
  source    = "./modules/ec2"
  instances = local.payload.instances
}

output "ec2_public_ips" {
  value = module.ec2.public_ips
}
