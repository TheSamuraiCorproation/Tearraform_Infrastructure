terraform {
  backend "s3" {
    bucket         = "thesamuraibucket"
    key            = "terraform/ec2/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "terraform-locks-ec2"
    encrypt        = true
  }
}

