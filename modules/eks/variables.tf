variable "aws_region" {
  type        = string
  description = "AWS region where EKS will be deployed"
}

variable "cluster_name" {
  type        = string
  description = "Name of the EKS cluster"
}

variable "kubernetes_version" {
  type        = string
  description = "Kubernetes version for the EKS cluster"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs for EKS"
}

