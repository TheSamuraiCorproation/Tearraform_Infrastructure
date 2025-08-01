resource "aws_instance" "this" {
  for_each = var.instances

  ami                    = each.value.ami
  instance_type          = each.value.instance_type
  user_data              = each.value.user_data != null ? each.value.user_data : null
  vpc_security_group_ids = each.value.security_groups
  key_name               = each.value.key_name
  tags                   = merge(
    {
      Name = each.value.name
    },
    each.value.tags
  )
  associate_public_ip_address = true

  # Ensure user_data sets up SSH if not provided
  user_data = each.value.user_data != null ? each.value.user_data : <<-EOF
              #!/bin/bash
              # Ensure .ssh directory exists and has proper permissions
              mkdir -p /home/ubuntu/.ssh
              chmod 700 /home/ubuntu/.ssh

              # The public key from key_name is injected by AWS
              chown ubuntu:ubuntu /home/ubuntu/.ssh -R
              EOF
}
