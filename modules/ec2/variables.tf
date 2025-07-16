variable "name" {
  type = string
}

variable "ami" {
  type = string
}

variable "instance_type" {
  type = string
}

variable "user_data" {
  type    = string
  default = ""
}
