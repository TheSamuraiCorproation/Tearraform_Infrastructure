variable "instances" {
  description = "Map of EC2 instance configurations"
  type        = map(object({
    ami                = string
    instance_type      = string
    user_data          = string
    name               = string
    security_groups    = list(string)
    key_name        = string 
    tags               = map(string)
    compliance_requirements = list(string)
  }))
}
