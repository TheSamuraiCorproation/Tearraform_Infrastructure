resource "aws_instance" "this" {
  ami                    = var.ami
  instance_type          = var.instance_type
  user_data              = var.user_data
  associate_public_ip_address = true

  tags = {
    Name = var.name
  }
}

output "public_ip" {
  value = aws_instance.this.public_ip
}

