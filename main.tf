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
  unique_cluster_name = "${local.payload.eks.cluster_name}-${replace(local.payload.user_name, " ", "-")}"
}

# Conditionally deploy EC2 module
module "ec2" {
  source    = "./modules/ec2"
  count     = local.payload.service_type == "ec2" ? 1 : 0
  instances = local.payload.instances
}

# Conditionally deploy EKS module
module "eks" {
  source = "./modules/eks"

  # use unique name 
  cluster_name       = local.unique_cluster_name
  kubernetes_version = try(local.payload.eks.kubernetes_version, "1.27")
  subnet_ids         = try(local.payload.eks.subnet_ids, [])
  vpc_id             = try(local.payload.eks.vpc_id, "")

  # Force Fargate for all EKS deployments. Ignore payload.node_group.
  use_fargate       = true
  # Accept selectors from payload if present, otherwise default to `default` namespace
  fargate_selectors = try(local.payload.eks.fargate_selectors, [{ "namespace" = "default" }])

  # keep node_group param present (module expects it) but we'll not use it when use_fargate = true
  node_group = try(local.payload.eks.node_group, {})
}



# Output EC2 public IPs (only relevant for EC2 scenario)
output "ec2_public_ips" {
  value = local.payload.service_type == "ec2" ? module.ec2[0].public_ips : null
}

# Output EKS cluster endpoint (only relevant for EKS scenario)
output "eks_cluster_endpoint" {
  value = local.payload.service_type == "eks" ? module.eks.cluster_endpoint : null
}
