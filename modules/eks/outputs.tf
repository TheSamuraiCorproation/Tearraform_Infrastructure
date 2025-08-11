output "cluster_id" {
  value = aws_eks_cluster.cluster.id
}

output "cluster_endpoint" {
  value = aws_eks_cluster.cluster.endpoint
}

output "cluster_certificate_authority_data" {
  value = aws_eks_cluster.cluster.certificate_authority[0].data
}

output "fargate_profile_name" {
  value = aws_eks_fargate_profile.fargate_profile.fargate_profile_name
}

output "cluster_name" {
  value = aws_eks_cluster.cluster.name
}

