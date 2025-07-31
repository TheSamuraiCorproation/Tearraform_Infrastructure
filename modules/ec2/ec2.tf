resource "aws_instance" "this" {
  for_each = var.instances

  ami                    = each.value.ami
  instance_type          = each.value.instance_type
  user_data              = each.value.user_data != null ? each.value.user_data : null
  vpc_security_group_ids = each.value.security_groups
  key_name               = each.value.key_name 
  tags = merge(
    {
      Name = each.value.name
    },
    each.value.tags
  )
  associate_public_ip_address = true
}
