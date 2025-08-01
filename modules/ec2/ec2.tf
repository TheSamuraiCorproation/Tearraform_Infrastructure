resource "aws_instance" "this" {
  for_each = var.instances

  ami                    = each.value.ami
  instance_type          = each.value.instance_type
  key_name               = "client-access-key"  # Use the Terraform-managed key pair
  vpc_security_group_ids = each.value.security_groups
  tags = merge(
    {
      Name = each.value.name
    },
    each.value.tags
  )
  associate_public_ip_address = true

  user_data = coalesce(each.value.user_data, <<-EOF
    #!/bin/bash
    # Ensure .ssh directory exists and has proper permissions
    mkdir -p /home/ubuntu/.ssh
    chmod 700 /home/ubuntu/.ssh

    # Ensure authorized_keys file exists and has correct permissions
    touch /home/ubuntu/.ssh/authorized_keys
    chmod 600 /home/ubuntu/.ssh/authorized_keys

    # The public key from key_name is injected by AWS into authorized_keys
    # Set ownership
    chown ubuntu:ubuntu /home/ubuntu/.ssh -R

    # Start and enable SSH service
    systemctl enable ssh --now

    # Wait briefly to ensure SSH is ready
    sleep 30
  EOF
  )
}
