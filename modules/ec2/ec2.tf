resource "aws_instance" "this" {
  for_each = var.instances

  ami           = "ami-0cebfb1f908092578" # Ubuntu 20.04 LTS in eu-central-1
  instance_type = each.value.instance_type
  key_name      = var.key_name             # Use the key_name passed from the root module
  vpc_security_group_ids = [var.security_group_id]
  subnet_id     = var.subnet_id

  associate_public_ip_address = true

  tags = merge(
    {
      "Name"        = each.key
      "Environment" = "Development"
      "Owner"       = each.value.owner
    },
    each.value.tags
  )

  user_data = <<-EOT
    #!/bin/bash
    # Ensure .ssh directory exists and has proper permissions
    mkdir -p /home/ubuntu/.ssh
    chmod 700 /home/ubuntu/.ssh
    
    # Ensure authorized_keys file exists and has correct permissions
    if [ ! -f /home/ubuntu/.ssh/authorized_keys ]; then
      touch /home/ubuntu/.ssh/authorized_keys
    fi
    chmod 600 /home/ubuntu/.ssh/authorized_keys
    
    # Copy the injected public key to authorized_keys
    cp /home/ubuntu/.ssh/authorized_keys.bak /home/ubuntu/.ssh/authorized_keys || true
    
    # Set ownership
    chown ubuntu:ubuntu /home/ubuntu/.ssh -R
    
    # Start and enable SSH service
    systemctl enable ssh --now
    
    # Wait longer to ensure SSH is fully ready
    sleep 180
  EOT

  user_data_replace_on_change = true

  lifecycle {
    ignore_changes = [user_data]
  }
}
