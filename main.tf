provider "aws" {
  region = var.aws_region
}

# Generate a unique suffix for the key name
resource "random_id" "unique_suffix" {
  byte_length = 4
}

# Generate RSA private key for EC2 key pair
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "ec2_key_pair" {
  key_name   = "client-access-key-${random_id.unique_suffix.hex}"
  public_key = tls_private_key.ec2_key.public_key_openssh

  lifecycle {
    ignore_changes = [key_name] # Ignore changes to key_name to prevent recreation
  }
}

output "private_key_pem" {
  value     = tls_private_key.ec2_key.private_key_pem
  sensitive = true
}

# Read JSON payload from S3 bucket/key
data "aws_s3_object" "payload" {
  bucket = var.s3_payload_bucket
  key    = var.s3_payload_key
}

locals {
  payload = jsondecode(data.aws_s3_object.payload.body)

  unique_cluster_name = local.payload.service_type == "eks" ? "${local.payload.eks.cluster_name}-${replace(local.payload.user_name, " ", "-")}" : ""
}

# Conditionally deploy EC2 if service_type == "ec2"
module "ec2" {
  source    = "./modules/ec2"
  count     = local.payload.service_type == "ec2" ? 1 : 0
  instances = local.payload.instances
  key_name  = aws_key_pair.ec2_key_pair.key_name # Pass the dynamic key_name
}

# Conditionally deploy EKS if service_type == "eks"
module "eks" {
  source             = "./modules/eks"
  count              = local.payload.service_type == "eks" ? 1 : 0
  cluster_name       = local.payload.eks.cluster_name
  kubernetes_version = local.payload.eks.kubernetes_version
  subnet_ids         = local.payload.eks.subnet_ids
  fargate_selectors  = lookup(local.payload.eks, "fargate_selectors", [
    {
      namespace = "default"
    }
  ])
}

# Outputs for EC2 public IPs (only when EC2 is deployed)
output "ec2_public_ips" {
  value = local.payload.service_type == "ec2" ? module.ec2[0].public_ips : null
}

# Outputs for EKS cluster endpoint (only when EKS is deployed)
output "eks_cluster_endpoint" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_endpoint : null
}

# Outputs for EKS cluster name (only when EKS is deployed)
output "cluster_name" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_name : null
}

# Outputs for EKS certificate authority data (only when EKS is deployed)
output "eks_cluster_certificate_authority_data" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_certificate_authority_data : null
}
