variable "cluster_name" {
  type = string
}

variable "kubernetes_version" {
  type = string
}

variable "subnet_ids" {
  type = list(string)
}

variable "node_group" {
  type = object({
    instance_type    = string
    desired_capacity = number
    max_size         = number
    min_size         = number
  })
}
