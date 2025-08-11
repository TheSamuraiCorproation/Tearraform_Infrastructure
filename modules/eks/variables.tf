variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version for the cluster"
  type        = string
  default     = "1.27"
}

variable "vpc_id" {
  description = "VPC id where EKS will be created"
  type        = string

}

variable "subnet_ids" {
  description = "List of subnet ids for EKS"
  type        = list(string)

}

variable "node_group" {
  description = "Node group configuration map (instance_type, desired_capacity, min_size, max_size)"
  type        = any
  default     = {}
}

variable "use_fargate" {
  description = "Whether to deploy pods on Fargate (true) or with a managed node group (false)"
  type        = bool
  default     = false
}

variable "fargate_selectors" {
  description = <<EOT
List of selector maps for Fargate profile. Each item should include "namespace" (string)
and optionally "labels" (map of string). Example:
[{ "namespace": "default" }, { "namespace": "my-app", "labels": {"app":"web"} }]
EOT
  type    = list(any)
  default = []
}

