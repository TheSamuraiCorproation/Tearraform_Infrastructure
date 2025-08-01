variable "instances" {
  description = "Map of EC2 instance configurations"
  type = map(object({
    ami                    = string
    instance_type          = string
    user_data              = optional(string)
    name                   = string
    security_groups        = list(string)
    key_name               = optional(string, "client-access-key")  # Default to Terraform-managed key
    tags                   = optional(map(string))
    compliance_requirements = optional(list(string))
    tools_to_install       = optional(list(string))
  }))
}
