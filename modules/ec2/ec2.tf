resource "aws_instance" "this" {
  for_each = var.instances

  ami           = each.value.ami
  instance_type = each.value.instance_type
  user_data     = each.value.user_data

  tags = {
    Name = each.value.name
  }

  associate_public_ip_address = true
}

output "public_ips" {
  value = { for k, v in aws_instance.this : k => v.public_ip }
}
