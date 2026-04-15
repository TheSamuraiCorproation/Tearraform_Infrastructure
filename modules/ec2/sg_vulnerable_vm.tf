# ---------------------------------------------------------------
# Fetch the pre-existing Kali VM to get its Elastic Public IP
# ---------------------------------------------------------------
data "aws_eip" "kali" {
  filter {
    name   = "tag:Name"
    values = ["kali-linux"]
  }
}

# ---------------------------------------------------------------
# Fetch the subnet to get the VPC ID (avoids needing var.vpc_id)
# ---------------------------------------------------------------
data "aws_subnet" "current" {
  id = var.subnet_id
}

locals {
  # Always open on every vulnerable VM regardless of attack selection
  always_open_ports = [
    { port = 22,   protocol = "tcp", description = "SSH"   },
    { port = 80,   protocol = "tcp", description = "HTTP"  },
    { port = 443,  protocol = "tcp", description = "HTTPS" },
    { port = 3306, protocol = "tcp", description = "MySQL" },
    { port = 53,   protocol = "tcp", description = "DNS TCP" },
    { port = 53,   protocol = "udp", description = "DNS UDP" },
    { port = 25,   protocol = "tcp", description = "SMTP" },
    { port = 3389, protocol = "tcp", description = "RDP" },
    { port = 514,  protocol = "udp", description = "Syslog UDP" },
  ]

  # Map: attack type -> ports to open
  # The attack names within each type may change over time,
  # but the four types themselves are stable
  type_port_map = {
    "web" = [
      { port = 3000, protocol = "tcp", description = "Vulnerable web app" }
    ]
    "ai" = [
      { port = 8080, protocol = "tcp", description = "Gemini sandbox" },
      { port = 8001, protocol = "tcp", description = "Crop service ML model" },
      { port = 5001, protocol = "tcp", description = "BERT service ML model" },
    ]
    "os" = [
      { port = 22, protocol = "tcp", description = "SSH for OS attacks" }
    ]
    "network" = [
      { port = 22,  protocol = "tcp", description = "SSH for network recon" },
      { port = 80,  protocol = "tcp", description = "HTTP for network recon" },
      { port = 443, protocol = "tcp", description = "HTTPS for network recon" },
    ]
  }

  # Extract unique attack types from the attacks array (attacks[].type)
  selected_types = distinct([
    for attack in var.attacks_to_enable :
    lookup(attack, "type", "")
  ])

  # Only include ports for attack types the user selected
  conditional_ports = flatten([
    for type, ports in local.type_port_map :
    ports if contains(local.selected_types, type)
  ])

  # Hash based on selected types so SG name changes when attack selection changes
  attacks_hash = md5(jsonencode(sort(local.selected_types)))

  # Final merged + deduplicated by port+protocol
  all_ingress_rules = [
    for key, rules in {
      for rule in concat(local.always_open_ports, local.conditional_ports) :
      "${rule.port}-${rule.protocol}" => rule...
    } :
    rules[0]
  ]
}

# ---------------------------------------------------------------
# Security Group resource for the user's vulnerable VM.
# A new SG is created per deployment, named with a random suffix
# and a hash of the selected attack types — so if the user picks
# a different combination of attacks, a completely fresh SG is
# created with the correct ports instead of reusing an old one.
# ---------------------------------------------------------------
resource "aws_security_group" "vulnerable_vm" {
  name        = "vulnerable-vm-sg-${random_id.unique_suffix.hex}-${local.attacks_hash}"
  description = "Dynamic SG for the user vulnerable VM - ports based on selected attacks"

  # VPC ID is derived from the subnet data source at the top of this file
  # rather than passed as a variable, keeping the variable surface minimal
  vpc_id      = data.aws_subnet.current.vpc_id

  # ---------------------------------------------------------------
  # Ingress rules — dynamically generated from local.all_ingress_rules
  # which is the merged + deduplicated list of:
  #   - always_open_ports (22, 80, 443, 3306, 53, 25, 3389, 514)
  #   - conditional ports based on the attack types the user selected
  # Every rule is scoped to the Kali machine's private IP only (/32)
  # so no other machine can reach these ports
  # ---------------------------------------------------------------
  dynamic "ingress" {
    for_each = local.all_ingress_rules
    content {
      description = ingress.value.description
      from_port   = ingress.value.port
      to_port     = ingress.value.port
      protocol    = ingress.value.protocol

      # Only the Kali machine (fetched via data source at top of file)
      # is allowed to reach the vulnerable VM ports
      cidr_blocks = ["${data.aws_eip.kali.public_ip}/32"]
    }
  }

  # ---------------------------------------------------------------
  # Egress — allow all outbound traffic so the VM can reach the
  # internet for package installs, ECR pulls, etc.
  # ---------------------------------------------------------------
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    # Name mirrors the resource name for easy identification in the AWS console
    Name      = "vulnerable-vm-sg-${random_id.unique_suffix.hex}-${local.attacks_hash}"
    ManagedBy = "Terraform"
  }

  # ---------------------------------------------------------------
  # create_before_destroy ensures a new SG is fully created before
  # the old one is destroyed when attack selection changes.
  # This prevents the instance from ever being left with no SG
  # attached during the replacement process.
  # ---------------------------------------------------------------
  lifecycle {
    create_before_destroy = true
  }
}
