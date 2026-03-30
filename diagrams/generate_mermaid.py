import json
import argparse
from datetime import datetime, UTC


def safe(value):
    if value is None:
        return "n/a"
    text = str(value)
    return text.replace('"', "'").replace("\n", " ").replace("\r", " ").strip()


def q(text):
    return safe(text).replace("\\", "\\\\").replace("\n", "\\n")


def header(lines):
    lines.extend([
        '%%{init: {"theme":"base","themeVariables":{'
        '"background":"#ffffff",'
        '"primaryColor":"#ffffff",'
        '"secondaryColor":"#f8fafc",'
        '"tertiaryColor":"#e2e8f0",'
        '"primaryTextColor":"#0f172a",'
        '"secondaryTextColor":"#0f172a",'
        '"tertiaryTextColor":"#0f172a",'
        '"lineColor":"#64748b",'
        '"fontFamily":"Inter, Arial, sans-serif"'
        '},"flowchart":{"htmlLabels":false,"curve":"basis","useMaxWidth":true}}}%%',
        "flowchart LR",
        "",
        'Client["Client / API Request"]',
        'S3["S3 Payload Bucket"]',
        'J["Jenkins Pipeline"]',
        'TF["Terraform Apply"]',
        'ANS["Ansible Configuration"]',
        "",
        "Client --> S3 --> J --> TF --> ANS",
        "",
        "style Client fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a",
        "style S3 fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a",
        "style J fill:#fff7ed,stroke:#f59e0b,stroke-width:1px,color:#0f172a",
        "style TF fill:#ecfccb,stroke:#84cc16,stroke-width:1px,color:#0f172a",
        "style ANS fill:#ecfccb,stroke:#84cc16,stroke-width:1px,color:#0f172a",
        "linkStyle default stroke:#64748b,stroke-width:1px",
        ""
    ])


def payload_block(lines, payload):
    lines.append("subgraph PAYLOAD [Deployment Payload]")
    lines.append("direction TB")

    file_name = q(payload.get("file_name", "n/a"))
    user_name = q(payload.get("user_name", "n/a"))
    client_email = q(payload.get("client_email", "n/a"))
    service_type = q(payload.get("service_type", "n/a"))

    lines.append(f'P1["File\\n{file_name}"]')
    lines.append(f'P2["User\\n{user_name}"]')
    lines.append(f'P3["Email\\n{client_email}"]')
    lines.append(f'P4["Service Type\\n{service_type}"]')

    lines.append("P1 --> P2 --> P3 --> P4")
    lines.append("end")
    lines.append("")
    lines.append("S3 --> P1")
    lines.append("")

    for node in ["P1", "P2", "P3", "P4"]:
        lines.append(f"style {node} fill:#f0f9ff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")
    lines.append("")


def collect_tools(payload):
    tools = []
    for inst_key, inst in payload.get("instances", {}).items():
        for tool in inst.get("tools_to_install", []):
            tools.append({
                "instance_key": inst_key,
                "name": tool.get("name", "unknown"),
                "repo": tool.get("ecr_repo_url", ""),
                "tag": tool.get("image_tag", "latest"),
                "run_args": tool.get("run_args", "")
            })
    return tools


def registry_block(lines, tools):
    repo_nodes = {}
    unique_repos = []
    seen = set()

    for tool in tools:
        repo = safe(tool["repo"]).strip()
        if repo and repo not in seen:
            seen.add(repo)
            unique_repos.append(repo)

    if not unique_repos:
        return repo_nodes

    lines.append("subgraph REGISTRY [Container Registry]")
    lines.append("direction TB")

    for idx, repo in enumerate(unique_repos, start=1):
        short_repo = repo.split("/")[-1]
        node = f"ECR_{idx}"
        repo_nodes[repo] = node
        lines.append(f'{node}["ECR Image\\n{q(short_repo)}"]')
        lines.append(f"style {node} fill:#fff1f2,stroke:#e11d48,stroke-width:1px,color:#0f172a")

    lines.append("end")
    lines.append("")
    return repo_nodes


def observability_block(lines, tools):
    names = {t["name"].lower() for t in tools}
    has_suricata = any("suricata" in n for n in names)
    has_elk = any(n in {"elk", "logstash", "kibana"} or "elk" in n for n in names)

    if not (has_suricata or has_elk):
        return

    lines.append("subgraph OBS [Observability]")
    lines.append("direction TB")

    if has_suricata:
        lines.append('OBS_SUR["Suricata\\nNetwork IDS"]')
        lines.append("style OBS_SUR fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

    if has_elk:
        lines.append('OBS_ELK["ELK Stack\\nLogs / Search / Dashboards"]')
        lines.append("style OBS_ELK fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")
        lines.append('OBS_KI["Kibana\\nDashboards"]')
        lines.append("style OBS_KI fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

    if has_suricata and has_elk:
        lines.append("OBS_SUR -->|alerts / logs| OBS_ELK")
        lines.append("OBS_ELK --> OBS_KI")

    lines.append("end")
    lines.append("")


def ec2_block(lines, payload, repo_nodes):
    lines.append("subgraph AWS_EC2 [AWS EC2 Lab]")
    lines.append("direction TB")

    for key, inst in payload.get("instances", {}).items():
        node_key = "".join(ch if ch.isalnum() else "_" for ch in str(key))
        node_id = f"EC2_{node_key}"

        instance_name = q(inst.get("name", "Unnamed"))
        instance_type = q(inst.get("instance_type", "unknown"))
        ami = q(inst.get("ami", "unknown"))
        subnet_id = q(inst.get("subnet_id", "unknown"))
        security_groups = ", ".join(q(x) for x in inst.get("security_groups", [])) or "none"

        lines.append(f"subgraph {node_id}_GROUP [Instance: {instance_name}]")
        lines.append("direction TB")

        lines.append(f'{node_id}["EC2 Instance\\n{instance_name}\\nType: {instance_type}\\nAMI: {ami}"]')
        lines.append(f"ANS --> {node_id}")
        lines.append(f"style {node_id} fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a")

        subnet_node = f"{node_id}_SUBNET"
        sg_node = f"{node_id}_SG"
        runtime_node = f"{node_id}_DOCKER"

        lines.append(f'{subnet_node}["Subnet\\n{subnet_id}"]')
        lines.append(f'{sg_node}["Security Groups\\n{security_groups}"]')
        lines.append(f'{runtime_node}["Docker Runtime"]')

        lines.append(f"style {subnet_node} fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a")
        lines.append(f"style {sg_node} fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a")
        lines.append(f"style {runtime_node} fill:#e0f2fe,stroke:#0284c7,stroke-width:1px,color:#0f172a")

        lines.append(f"{subnet_node} --> {node_id}")
        lines.append(f"{sg_node} --> {node_id}")
        lines.append(f"{node_id} --> {runtime_node}")

        tools = inst.get("tools_to_install", [])
        tool_nodes = []

        for idx, tool in enumerate(tools, start=1):
            tool_name = q(tool.get("name", "unknown"))
            repo = safe(tool.get("ecr_repo_url", "")).strip()
            tag = q(tool.get("image_tag", "latest"))
            run_args = q(tool.get("run_args", ""))

            tool_node = f"{node_id}_TOOL_{idx}"
            tool_nodes.append((tool_node, tool_name.lower(), repo))

            image_name = q(repo.split("/")[-1] if repo else "n/a")
            lines.append(f'{tool_node}["{tool_name}\\nImage: {image_name}:{tag}\\n{run_args}"]')
            lines.append(f"{runtime_node} --> {tool_node}")
            lines.append(f"style {tool_node} fill:#cffafe,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

            if repo and repo in repo_nodes:
                lines.append(f"{repo_nodes[repo]} --> {runtime_node}")

        sur_node = next((n for n, name, _ in tool_nodes if "suricata" in name), None)
        elk_node = next((n for n, name, _ in tool_nodes if name in {"elk", "logstash", "kibana"} or "elk" in name), None)
        if sur_node and elk_node:
            lines.append(f"{sur_node} -->|alerts / logs| {elk_node}")

        lines.append("end")
        lines.append("")

    lines.append("end")
    lines.append("")


def eks_block(lines, payload):
    lines.append("subgraph AWS_EKS [AWS EKS Lab]")
    lines.append("direction TB")

    cluster_name = q(payload.get("cluster_name", "EKS Cluster"))
    lines.append(f'EKS["{cluster_name}"]')
    lines.append("style EKS fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a")

    for idx, group in enumerate(payload.get("node_groups", []), start=1):
        ng = f"EKS_NG_{idx}"
        ng_name = q(group.get("name", f"ng-{idx}"))
        lines.append(f'{ng}["Node Group\\n{ng_name}"]')
        lines.append(f"style {ng} fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a")
        lines.append(f"EKS --> {ng}")

    lines.append("end")
    lines.append("")


def outputs_block(lines):
    lines.append("subgraph OUTPUTS [Outputs]")
    lines.append("direction TB")
    lines.append('OUT_SVG["SVG\\nBest for docs / zoom"]')
    lines.append('OUT_PNG["PNG\\nHigh-resolution export"]')
    lines.append('OUT_LOGS["Jenkins Console\\nBuild trace"]')
    lines.append("style OUT_SVG fill:#f8fafc,stroke:#334155,stroke-width:1px,color:#0f172a")
    lines.append("style OUT_PNG fill:#f8fafc,stroke:#334155,stroke-width:1px,color:#0f172a")
    lines.append("style OUT_LOGS fill:#f8fafc,stroke:#334155,stroke-width:1px,color:#0f172a")
    lines.append("end")
    lines.append("")
    lines.append("J --> OUT_SVG")
    lines.append("J --> OUT_PNG")
    lines.append("J --> OUT_LOGS")
    lines.append("")


def footer(lines):
    ts = datetime.now(UTC).isoformat()
    lines.append(f'NOTE["Generated automatically\\n{q(ts)}"]')
    lines.append("style NOTE fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 4 3,stroke-width:1px,color:#0f172a")


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

    tools = collect_tools(payload)
    repo_nodes = registry_block(lines, tools)
    observability_block(lines, tools)

    service_type = str(payload.get("service_type", "")).lower().strip()
    if service_type == "ec2":
        ec2_block(lines, payload, repo_nodes)
    elif service_type == "eks":
        eks_block(lines, payload)
    else:
        lines.append('UNKNOWN["Unknown service_type"]')
        lines.append("style UNKNOWN fill:#f8fafc,stroke:#334155,stroke-width:1px,color:#0f172a")

    outputs_block(lines)
    footer(lines)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[OK] Mermaid diagram generated")


if __name__ == "__main__":
    main()
