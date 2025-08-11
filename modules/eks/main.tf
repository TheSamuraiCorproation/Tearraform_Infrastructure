terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.3.0"
    }
  }
}

#############
# IAM: cluster role
#############
resource "aws_iam_role" "eks_cluster_role" {
  name = "${var.cluster_name}-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })

  force_detach_policies = true
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

#############
# Security Group for cluster (control plane)
#############
resource "aws_security_group" "eks_cluster" {
  name        = "${var.cluster_name}-sg"
  description = "Security group for EKS cluster ${var.cluster_name}"
  vpc_id      = var.vpc_id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.cluster_name}-sg"
  }
}

#############
# EKS cluster (control plane)
#############
resource "aws_eks_cluster" "cluster" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = false
    endpoint_public_access  = true
    security_group_ids      = [aws_security_group.eks_cluster.id]
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

#############
# Normalize fargate selectors (accept strings or maps)
#############
locals {
  fargate_input = length(var.fargate_selectors) > 0 ? var.fargate_selectors : [{ "namespace" = "default" }]

  normalized_fargate_selectors = [
    for s in local.fargate_input : (
      // if s is a string -> produce object { namespace = s, labels = {} }
      can(regex(".*", s)) ?
      {
        namespace = s
        labels    = {}
      } :
      // otherwise assume map/object with namespace (or fallback)
      {
        namespace = lookup(s, "namespace", tostring(s))
        labels    = lookup(s, "labels", {})
      }
    )
  ]
}

#############
# Fargate Pod Execution Role & Attachment (only if use_fargate)
#############
resource "aws_iam_role" "fargate_pod_execution_role" {
  count = var.use_fargate ? 1 : 0

  name = "${var.cluster_name}-fargate-pod-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Service = "eks-fargate-pods.amazonaws.com"
      }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "fargate_pod_exec_policy" {
  count      = var.use_fargate ? 1 : 0
  role       = aws_iam_role.fargate_pod_execution_role[0].name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSFargatePodExecutionRolePolicy"
}

#############
# Fargate Profile
#############
resource "aws_eks_fargate_profile" "fargate" {
  count                  = var.use_fargate ? 1 : 0
  cluster_name           = aws_eks_cluster.cluster.name
  fargate_profile_name   = "${var.cluster_name}-fp"
  pod_execution_role_arn = aws_iam_role.fargate_pod_execution_role[0].arn
  subnet_ids             = var.subnet_ids
  depends_on             = [aws_iam_role_policy_attachment.fargate_pod_exec_policy, aws_eks_cluster.cluster]

  dynamic "selector" {
    for_each = local.normalized_fargate_selectors
    content {
      namespace = selector.value.namespace
      # labels is optional, only set when non-empty map
      labels = length(keys(selector.value.labels)) > 0 ? selector.value.labels : {}
    }
  }
}

#############
# Outputs
#############
output "cluster_name" {
  value = aws_eks_cluster.cluster.name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.cluster.endpoint
}

output "cluster_certificate_authority_data" {
  value = aws_eks_cluster.cluster.certificate_authority[0].data
}
