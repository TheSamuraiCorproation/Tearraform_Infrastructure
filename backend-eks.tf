terraform {
  backend "s3" {
    bucket         = "thesamuraibucket"
    key            = "terraform/eks/terraform.tfstate"
    region         = "eu-central-1"
    dynamodb_table = "terraform-locks-eks"
    encrypt        = true
  }
}

