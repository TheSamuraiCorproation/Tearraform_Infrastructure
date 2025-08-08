terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.3.0"
    }
  }
}

resource "aws_eks_cluster" "cluster" {
  name     = var.cluster_name
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = false
    endpoint_public_access  = true
  }

  depends_on = [aws_iam_role_policy_attachment.eks_cluster_policy]
}

resource "aws_eks_node_group" "node_group" {
  cluster_name    = aws_eks_cluster.cluster.name
  node_group_name = "managed-node-group"
  node_role_arn   = aws_iam_role.eks_node_role.arn
  subnet_ids      = var.subnet_ids

  scaling_config {
    desired_size = var.node_group.desired_capacity
    max_size     = var.node_group.max_size
    min_size     = var.node_group.min_size
  }

  instance_types = [var.node_group.instance_type]

  depends_on = [aws_iam_role_policy_attachment.eks_worker_policy, aws_iam_role_policy_attachment.eks_cni_policy]
}

resource "aws_iam_role" "eks_cluster_role" {
  name               = "${var.cluster_name}-cluster-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Effect = "Allow"
      Principal = { Service = "eks.amazonaws.com" }
    }]
  })
  force_detach_policies = true
}

resource "aws_iam_role" "eks_node_role" {
  name               = "${var.cluster_name}-node-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = ["sts:AssumeRole", "sts:TagSession"]
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
  force_detach_policies = true
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}

resource "aws_iam_role_policy_attachment" "eks_worker_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  role       = aws_iam_role.eks_node_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSVPCResourceController"
}

# Data source to get the EKS cluster details
data "aws_eks_cluster" "cluster" {
  name = aws_eks_cluster.cluster.name
}

# Security group rule for node-to-control-plane communication (port 1025)
resource "aws_security_group_rule" "node_to_control_plane_1025" {
  type              = "ingress"
  from_port         = 1025
  to_port           = 1025
  protocol          = "tcp"
  security_group_id = "sg-08bb32aa5dd0cb5a0" # Update with your SG ID
  source_security_group_id = tolist(data.aws_eks_cluster.cluster.vpc_config[0].security_group_ids)[0]
}

# Security group rule for node-to-control-plane communication (ports 30000-32767)
resource "aws_security_group_rule" "node_to_control_plane_30000_32767" {
  type              = "ingress"
  from_port         = 30000
  to_port           = 32767
  protocol          = "tcp"
  security_group_id = "sg-08bb32aa5dd0cb5a0" # Update with your SG ID
  source_security_group_id = tolist(data.aws_eks_cluster.cluster.vpc_config[0].security_group_ids)[0]
}

# Security group rule for node-to-control-plane communication (port 443)
resource "aws_security_group_rule" "node_to_control_plane_443" {
  type              = "ingress"
  from_port         = 443
  to_port           = 443
  protocol          = "tcp"
  security_group_id = "sg-08bb32aa5dd0cb5a0" # Update with your SG ID
  source_security_group_id = tolist(data.aws_eks_cluster.cluster.vpc_config[0].security_group_ids)[0]
}

# Security group rule for node-to-node communication
resource "aws_security_group_rule" "node_to_node" {
  type              = "ingress"
  from_port         = 0
  to_port           = 65535
  protocol          = "-1"
  security_group_id = "sg-08bb32aa5dd0cb5a0" # Update with your SG ID
  source_security_group_id = "sg-08bb32aa5dd0cb5a0"
}

# Ensure outbound rule allows all traffic
resource "aws_security_group_rule" "outbound_all" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  security_group_id = "sg-08bb32aa5dd0cb5a0" # Update with your SG ID
  cidr_blocks       = ["0.0.0.0/0"]
}

output "cluster_endpoint" {
  value = aws_eks_cluster.cluster.endpoint
}
