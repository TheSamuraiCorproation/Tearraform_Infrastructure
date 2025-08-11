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
  default     = ""
}

variable "subnet_ids" {
  description = "List of subnet ids for EKS"
  type        = list(string)
  default     = []
}

variable "use_fargate" {
  description = "Whether to deploy pods on Fargate (true) or not"
  type        = bool
  default     = true
}

variable "fargate_selectors" {
  description = <<EOT
List of selectors for the Fargate profile. Accepts:
- list of strings: ["default", "my-app"]
- list of maps/objects: [{ namespace = "default" }, { namespace = "my-app", labels = { app = "web" } }]
If empty, module will default to [{ namespace = "default" }].
EOT
  type    = list(any)
  default = []
}

