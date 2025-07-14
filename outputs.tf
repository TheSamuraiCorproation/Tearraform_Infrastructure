output "instance_public_ips" {
  value = { for k, inst in module.ec2 : k => inst.public_ip }
}

