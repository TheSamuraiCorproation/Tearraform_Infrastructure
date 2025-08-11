output "ec2_public_ips" {
  value       = local.payload.service_type == "ec2" ? module.ec2[0].public_ips : null
  description = "Public IPs of the EC2 instances"
}

output "eks_cluster_endpoint" {
  value       = local.payload.service_type == "eks" ? module.eks[0].cluster_endpoint : null
  description = "Endpoint URL of the EKS cluster"
}

output "cluster_name" {
  value       = local.payload.service_type == "eks" ? module.eks[0].cluster_name : null
  description = "Name of the EKS cluster"
}

output "private_key_pem" {
  value       = tls_private_key.ec2_key.private_key_pem
  description = "Private key PEM used for EC2 key pair"
  sensitive   = true
}

