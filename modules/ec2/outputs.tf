output "public_ips" {
  value = { for k, v in aws_instance.this : k => v.public_ip }
}

output "ec2_public_ips" {
  value = { for k, v in aws_instance.this : k => v.public_ip }
}
