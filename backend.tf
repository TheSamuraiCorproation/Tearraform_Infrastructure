terraform {
  backend "s3" {
    bucket         = "thesamuraibucket"
    key            = "terraform/state.tfstate"
    region         = "eu-central-1"
    use_lockfile   = true 

  }
}
