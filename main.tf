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

# Conditionally deploy EC2 module
module "ec2" {
  source    = "./modules/ec2"
  count     = local.payload.service_type == "ec2" ? 1 : 0
  instances = local.payload.instances
}

# Conditionally deploy EKS module
module "eks" {
  source    = "./modules/eks"
  count     = local.payload.service_type == "eks" ? 1 : 0
  cluster_name      = local.payload.eks.cluster_name
  kubernetes_version = local.payload.eks.kubernetes_version
  subnet_ids        = ["subnet-0c58b996aad07a170", "subnet-044990a3c6441fbe0", "subnet-0988f4f0d595fe16d", "subnet-05a6ed5c6fe9e38d4", "subnet-04069d2231aa7c333", "subnet-0088e54045744e01e"]
  node_group        = local.payload.eks.node_group
  providers = {
    aws = aws
  }
}

# Output EC2 public IPs (only relevant for EC2 scenario)
output "ec2_public_ips" {
  value = local.payload.service_type == "ec2" ? module.ec2[0].public_ips : null
}

# Output EKS cluster endpoint (only relevant for EKS scenario)
output "eks_cluster_endpoint" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_endpoint : null
}
