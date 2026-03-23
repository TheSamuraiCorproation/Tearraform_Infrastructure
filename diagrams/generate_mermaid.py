import json
import argparse
from datetime import datetime, UTC


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
        "",
        "%% ===== Main flow =====",
        "Client[Client / API Request]",
        "S3[S3 Payload Bucket]",
        "J[Jenkins Pipeline]",
        "TF[Terraform Apply]",
        "ANS[Ansible Configuration]",
        "Client --> S3 --> J --> TF --> ANS",
        "",
        "class Client,S3 external;",
        "class J orchestrator;",
        "class TF provisioner;",
        "class ANS provisioner;",
        ""
    ])


def ec2_diagram(lines, payload):
    lines.append("subgraph AWS_EC2 [AWS EC2 Lab]")
    lines.append("direction TB")

    for key, inst in payload["instances"].items():
        node_id = f"EC2_{key.replace('-', '_')}"
        instance_name = inst.get("name", "Unnamed")
        instance_type = inst.get("instance_type", "unknown")
        subnet_id = inst.get("subnet_id", "unknown")
        security_groups = ", ".join(inst.get("security_groups", [])) or "none"

        lines.append(
            f'{node_id}["<b>EC2 Instance</b><br/>{instance_name}<br/>'
            f'Type: {instance_type}<br/>Subnet: {subnet_id}<br/>SGs: {security_groups}"]'
        )
        lines.append(f"ANS --> {node_id}")
        lines.append(f"class {node_id} compute;")

        tools = inst.get("tools_to_install", [])
        if tools:
            for idx, tool in enumerate(tools, start=1):
                tool_name = tool.get("name", "unknown")
                ecr_repo = tool.get("ecr_repo_url", "n/a")
                image_tag = tool.get("image_tag", "latest")
                run_args = tool.get("run_args", "")

                tool_node = f"{node_id}_TOOL_{idx}"
                lines.append(
                    f'{tool_node}["<b>{tool_name}</b><br/>'
                    f'ECR: {ecr_repo}<br/>Tag: {image_tag}<br/>'
                    f'{run_args}"]'
                )
                lines.append(f"{node_id} --> {tool_node}")
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


def outputs_block(lines, payload):
    lines.append("subgraph OUTPUTS [Outputs]")
    lines.append("direction TB")
    lines.append('ART["Rendered Diagram<br/>PNG / SVG"]')
    lines.append('LOGS["Build Logs<br/>Jenkins Console"]')
    lines.append("class ART output;")
    lines.append("class LOGS output;")
    lines.append("end")
    lines.append("")
    lines.append("J --> ART")
    lines.append("J --> LOGS")
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

    with open(args.payload) as f:
        payload = json.load(f)

    lines = []
    header(lines)

    if payload.get("service_type") == "ec2":
        ec2_diagram(lines, payload)
    elif payload.get("service_type") == "eks":
        eks_diagram(lines, payload)

    outputs_block(lines, payload)
    footer(lines)

    with open(args.out, "w") as f:
        f.write("\n".join(lines))

    print("[OK] Mermaid diagram generated")


if __name__ == "__main__":
    main()
