output "cluster_name" {
  value = local.payload.service_type == "eks" ? module.eks[0].cluster_name : null
  description = "EKS cluster name output from the eks module"
}

