variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs"
  type        = list(string)
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.29"
}

variable "fargate_selectors" {
  description = "List of Fargate selectors with optional labels"
  type = list(object({
    namespace = string
    labels    = optional(map(string))
  }))
  default = [
    {
      namespace = "default"
    }
  ]
}

