# ---------------------------------------------------------------
# Fetch the pre-existing Kali VM to get its private IP
# ---------------------------------------------------------------
data "aws_instance" "kali" {
  instance_id = "i-0c2181477f34261e3"
}

# ---------------------------------------------------------------
# Fetch the subnet to get the VPC ID (avoids needing var.vpc_id)
# ---------------------------------------------------------------
data "aws_subnet" "current" {
  id = var.subnet_id
}

locals {
  # Always open on every vulnerable VM
  always_open_ports = [
    { port = 22,  protocol = "tcp", description = "SSH"   },
    { port = 80,  protocol = "tcp", description = "HTTP"  },
    { port = 443, protocol = "tcp", description = "HTTPS" },
  ]

  # Map: tool name (from attacks[].tool in payload) → ports to open
  tool_port_map = {
    "nmap"      = [{ port = 22,   protocol = "tcp", description = "SSH for nmap"       }]
    "nikto"     = [{ port = 3000, protocol = "tcp", description = "Vulnerable web app" }]
    "metasploit"= [{ port = 3389, protocol = "tcp", description = "RDP"                },
                   { port = 445,  protocol = "tcp", description = "SMB"                }]
    "sqlmap"    = [{ port = 3306, protocol = "tcp", description = "MySQL"              }]
    "hydra"     = [{ port = 22,   protocol = "tcp", description = "SSH brute force"    },
                   { port = 3306, protocol = "tcp", description = "MySQL brute force"  }]
    "smtp_tool" = [{ port = 25,   protocol = "tcp", description = "SMTP"               }]
    "dns_tool"  = [{ port = 53,   protocol = "tcp", description = "DNS TCP"            },
                   { port = 53,   protocol = "udp", description = "DNS UDP"            }]
    "rdp_tool"  = [{ port = 3389, protocol = "tcp", description = "RDP"               }]
    "syslog"    = [{ port = 514,  protocol = "udp", description = "Syslog UDP"        }]
  }

  # Extract tool names from the attacks array (attacks[].tool)
  selected_tools = [
    for attack in var.attacks_to_enable :
    lookup(attack, "tool", "")
  ]

  # Only include ports for tools the user actually selected
  conditional_ports = flatten([
    for tool, ports in local.tool_port_map :
    ports if contains(local.selected_tools, tool)
  ])

  # Final merged + deduplicated list
  all_ingress_rules = distinct(concat(local.always_open_ports, local.conditional_ports))
}

resource "aws_security_group" "vulnerable_vm" {
  name        = "vulnerable-vm-sg-${random_id.unique_suffix.hex}"
  description = "Dynamic SG for the user vulnerable VM — ports based on selected attacks"
  vpc_id      = data.aws_subnet.current.vpc_id

  dynamic "ingress" {
    for_each = local.all_ingress_rules
    content {
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol
      cidr_blocks = ["${data.aws_instance.kali.private_ip}/32"]
    }
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name      = "vulnerable-vm-sg-${random_id.unique_suffix.hex}"
    ManagedBy = "Terraform"
  }
}
