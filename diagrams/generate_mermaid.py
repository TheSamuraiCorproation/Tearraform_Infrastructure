import json
import argparse
from datetime import datetime, UTC


def safe(value):
    """
    Make text safer for Mermaid labels.
    """
    if value is None:
        return "n/a"
    text = str(value)
    return (
        text.replace('"', "'")
            .replace("\n", " ")
            .replace("\r", " ")
            .strip()
    )


def header(lines):
    lines.extend([
        "flowchart LR",
        "",
        "%% ===== Styles =====",
        "classDef external fill:#eef4ff,stroke:#7b8cff,stroke-width:1px,color:#111;",
        "classDef orchestrator fill:#fff3cd,stroke:#d6a200,stroke-width:1px,color:#111;",
        "classDef provisioner fill:#e8f7e8,stroke:#4caf50,stroke-width:1px,color:#111;",
        "classDef compute fill:#f3e8ff,stroke:#a855f7,stroke-width:1px,color:#111;",
        "classDef container fill:#e0f2fe,stroke:#0284c7,stroke-width:1px,color:#111;",
        "classDef output fill:#fce7f3,stroke:#db2777,stroke-width:1px,color:#111;",
        "classDef note fill:#f8fafc,stroke:#94a3b8,stroke-dasharray: 4 3,color:#334155;",
        "classDef payload fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#111;",
        "",
        "%% ===== Main flow =====",
        'Client["Client / API Request"]',
        'S3["S3 Payload Bucket"]',
        'J["Jenkins Pipeline"]',
        'TF["Terraform Apply"]',
        'ANS["Ansible Configuration"]',
        "",
        "Client --> S3 --> J --> TF --> ANS",
        "",
        "class Client,S3 payload;",
        "class J orchestrator;",
        "class TF provisioner;",
        "class ANS provisioner;",
        ""
    ])


def payload_block(lines, payload):
    lines.append("subgraph PAYLOAD [Deployment Payload]")
    lines.append("direction TB")

    file_name = safe(payload.get("file_name", "n/a"))
    user_name = safe(payload.get("user_name", "n/a"))
    client_email = safe(payload.get("client_email", "n/a"))
    service_type = safe(payload.get("service_type", "n/a"))

    lines.append(f'P1["<b>File</b><br/>{file_name}"]')
    lines.append(f'P2["<b>User</b><br/>{user_name}"]')
    lines.append(f'P3["<b>Email</b><br/>{client_email}"]')
    lines.append(f'P4["<b>Service</b><br/>{service_type}"]')

    lines.append("P1 --> P2 --> P3 --> P4")
    lines.append("class P1,P2,P3,P4 payload;")
    lines.append("end")
    lines.append("")
    lines.append("S3 --> P1")
    lines.append("")


def ec2_diagram(lines, payload):
    lines.append("subgraph AWS_EC2 [AWS EC2 Lab]")
    lines.append("direction TB")

    instances = payload.get("instances", {})
    for key, inst in instances.items():
        node_id = f"EC2_{key.replace('-', '_')}"

        instance_name = safe(inst.get("name", "Unnamed"))
        instance_type = safe(inst.get("instance_type", "unknown"))
        subnet_id = safe(inst.get("subnet_id", "unknown"))
        security_groups = ", ".join([safe(x) for x in inst.get("security_groups", [])]) or "none"
        ami = safe(inst.get("ami", "unknown"))

        # Main instance
        lines.append(
            f'{node_id}["<b>EC2 Instance</b><br/>{instance_name}<br/>'
            f'Type: {instance_type}<br/>AMI: {ami}"]'
        )
        lines.append(f"ANS --> {node_id}")
        lines.append(f"class {node_id} compute;")

        # Network / security layer
        subnet_node = f"{node_id}_SUBNET"
        sg_node = f"{node_id}_SG"

        lines.append(f'{subnet_node}["<b>Subnet</b><br/>{subnet_id}"]')
        lines.append(f'{sg_node}["<b>Security Groups</b><br/>{security_groups}"]')

        lines.append(f"{subnet_node} --> {node_id}")
        lines.append(f"{sg_node} --> {node_id}")
        lines.append(f"class {subnet_node} external;")
        lines.append(f"class {sg_node} external;")

        # Container runtime
        docker_node = f"{node_id}_DOCKER"
        lines.append(f'{docker_node}["<b>Docker Runtime</b>"]')
        lines.append(f"{node_id} --> {docker_node}")
        lines.append(f"class {docker_node} container;")

        # Tools
        tools = inst.get("tools_to_install", [])
        if tools:
            for idx, tool in enumerate(tools, start=1):
                tool_name = safe(tool.get("name", "unknown"))
                ecr_repo = safe(tool.get("ecr_repo_url", "n/a"))
                image_tag = safe(tool.get("image_tag", "latest"))
                run_args = safe(tool.get("run_args", ""))

                short_repo = ecr_repo.split("/")[-1] if "/" in ecr_repo else ecr_repo

                tool_node = f"{node_id}_TOOL_{idx}"
                lines.append(
                    f'{tool_node}["<b>{tool_name}</b><br/>'
                    f'Image: {short_repo}:{image_tag}<br/>'
                    f'{run_args}"]'
                )
                lines.append(f"{docker_node} --> {tool_node}")
                lines.append(f"class {tool_node} container;")

    lines.append("end")
    lines.append("")


def eks_diagram(lines, payload):
    lines.append("subgraph AWS_EKS [AWS EKS Lab]")
    lines.append("direction TB")
    lines.append('EKS["<b>EKS Cluster</b>"]')
    lines.append("ANS --> EKS")
    lines.append("class EKS compute;")
    lines.append("end")
    lines.append("")


def outputs_block(lines):
    lines.append("subgraph OUTPUTS [Outputs]")
    lines.append("direction TB")
    lines.append('ART["<b>Rendered Diagram</b><br/>PNG / SVG"]')
    lines.append('LOGS["<b>Build Logs</b><br/>Jenkins Console"]')
    lines.append('META["<b>Documentation Ready</b><br/>Architecture View"]')
    lines.append("class ART,LOGS,META output;")
    lines.append("end")
    lines.append("")
    lines.append("J --> ART")
    lines.append("J --> LOGS")
    lines.append("J --> META")
    lines.append("")


def footer(lines):
    ts = datetime.now(UTC).isoformat()
    lines.append(f'NOTE["Generated automatically<br/>{ts}"]')
    lines.append("class NOTE note;")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as f:
        payload = json.load(f)

    lines = []
    header(lines)
    payload_block(lines, payload)

    service_type = payload.get("service_type", "").lower()
    if service_type == "ec2":
        ec2_diagram(lines, payload)
    elif service_type == "eks":
        eks_diagram(lines, payload)
    else:
        lines.append('UNKNOWN["<b>Unknown service_type</b>"]')
        lines.append("class UNKNOWN external;")
        lines.append("")

    outputs_block(lines)
    footer(lines)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[OK] Mermaid diagram generated")


if __name__ == "__main__":
    main()
