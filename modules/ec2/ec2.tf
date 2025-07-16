resource "aws_instance" "this" {e
  ami           = var.ami
  instance_type = var.instance_type
  user_data     = var.user_data

  tags = {
    Name = var.name
  }

  associate_public_ip_address = true
}

output "public_ip" {
  value = aws_instance.this.public_ip
}
