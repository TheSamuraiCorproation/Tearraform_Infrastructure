provider "aws" {
  region = var.aws_region
}

# Generate a unique suffix for the key name (used only for EC2)
resource "random_id" "unique_suffix" {
  byte_length = 4
  count       = local.payload.service_type == "ec2" ? 1 : 0
}

# Generate RSA private key for EC2 key pair (only for EC2)
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
  count     = local.payload.service_type == "ec2" ? 1 : 0
}

resource "aws_key_pair" "ec2_key_pair" {
  count     = local.payload.service_type == "ec2" ? 1 : 0
  key_name   = "client-access-key-${random_id.unique_suffix[0].hex}"
  public_key = tls_private_key.ec2_key[0].public_key_openssh

  lifecycle {
    ignore_changes = [key_name]
  }
}

output "private_key_pem" {
  value     = local.payload.service_type == "ec2" ? tls_private_key.ec2_key[0].private_key_pem : null
  sensitive = true
}

# Read JSON payload from S3 bucket/key
data "aws_s3_object" "payload" {
  bucket = var.s3_payload_bucket
  key    = var.s3_payload_key
}

locals {
  payload = jsondecode(data.aws_s3_object.payload.body)

  # EC2-specific locals
  instance_keys    = local.payload.service_type == "ec2" ? keys(local.payload.instances) : []
  instance_config  = local.payload.service_type == "ec2" ? local.payload.instances[local.instance_keys[0]] : null

  # EKS-specific locals (only defined if service_type is eks)
  unique_cluster_name = local.payload.service_type == "eks" ? "${local.payload.eks.cluster_name}-${replace(local.payload.user_name, " ", "-")}" : ""
}

# Conditionally deploy EC2 if service_type == "ec2"
module "ec2" {
  source           = "./modules/ec2"
  count            = local.payload.service_type == "ec2" ? 1 : 0
  instances        = local.payload.instances
  key_name         = aws_key_pair.ec2_key_pair[0].key_name
  security_group_id = local.instance_config != null ? local.instance_config.security_groups[0] : null
  subnet_id        = local.instance_config != null ? local.instance_config.subnet_id : null
}

# Conditionally deploy EKS if service_type == "eks"
module "eks" {
  source             = "./modules/eks"
  count              = local.payload.service_type == "eks" ? 1 : 0
  cluster_name       = local.payload.service_type == "eks" ? local.payload.eks.cluster_name : null
  kubernetes_version = local.payload.service_type == "eks" ? local.payload.eks.kubernetes_version : null
  subnet_ids         = local.payload.service_type == "eks" ? local.payload.eks.subnet_ids : null
  fargate_selectors  = local.payload.service_type == "eks" ? lookup(local.payload.eks, "fargate_selectors", [
    { namespace = "default" }
  ]) : null
}

# Outputs for EC2 public IPs (only when EC2 is deployed)
output "ec2_public_ips" {
  value = local.payload.service_type == "ec2" ? module.ec2[0].public_ips : null
}

# Outputs for EKS cluster details (only when EKS is deployed)
output "cluster_name" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_name : null
}

output "eks_cluster_endpoint" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_endpoint : null
}

output "eks_cluster_certificate_authority_data" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_certificate_authority_data : null
}
