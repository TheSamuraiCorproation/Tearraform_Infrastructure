import json
import argparse
import html
from datetime import datetime, UTC


def safe(value):
    if value is None:
        return "n/a"
    text = str(value)
    return text.replace('"', "'").replace("\n", " ").replace("\r", " ").strip()


def q(text):
    return safe(text).replace("\\", "\\\\").replace("\n", "\\n")


def slug(value):
    return "".join(ch if ch.isalnum() else "_" for ch in str(value))


def short(text, limit=60):
    s = safe(text)
    return s if len(s) <= limit else s[: limit - 1] + "…"


def icon_for_tool(name):
    n = safe(name).lower()
    if "suricata" in n:
        return "🛡️"
    if n in {"elk", "logstash", "kibana"} or "elk" in n:
        return "📊"
    if "docker" in n:
        return "🐳"
    return "📦"


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
        '},"flowchart":{"htmlLabels":false,"curve":"basis","useMaxWidth":true,"nodeSpacing":60,"rankSpacing":80,"diagramPadding":18}}}%%',
        "flowchart LR",
        "",
        "classDef external fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a;",
        "classDef orchestrator fill:#fff7ed,stroke:#f59e0b,stroke-width:1px,color:#0f172a;",
        "classDef provisioner fill:#ecfccb,stroke:#84cc16,stroke-width:1px,color:#0f172a;",
        "classDef compute fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a;",
        "classDef runtime fill:#e0f2fe,stroke:#0284c7,stroke-width:1px,color:#0f172a;",
        "classDef container fill:#cffafe,stroke:#06b6d4,stroke-width:1px,color:#0f172a;",
        "classDef registry fill:#fff1f2,stroke:#e11d48,stroke-width:1px,color:#0f172a;",
        "classDef security fill:#ecfeff,stroke:#0891b2,stroke-width:1px,color:#0f172a;",
        "classDef note fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 4 3,stroke-width:1px,color:#0f172a;",
        "",
        'Client["👤 Client / API Request"]',
        'S3["🪣 S3 Payload Bucket"]',
        'J["🧪 Jenkins Pipeline"]',
        'TF["🔧 Terraform Apply"]',
        'ANS["🛠️ Ansible Configuration"]',
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
    attacks = payload.get("attacks", [])
    attack_summary = ", ".join(
        f"{safe(a.get('tool', 'tool'))} ({safe(a.get('type', 'attack'))})"
        for a in attacks
    ) or "none"

    lines.append("subgraph PAYLOAD [Deployment Payload]")
    lines.append("direction TB")

    file_name = q(payload.get("file_name", "n/a"))
    user_name = q(payload.get("user_name", "n/a"))
    client_email = q(payload.get("client_email", "n/a"))
    service_type = q(payload.get("service_type", "n/a"))

    lines.append(f'P1["📄 File\\n{file_name}"]')
    lines.append(f'P2["👤 User\\n{user_name}"]')
    lines.append(f'P3["✉️ Email\\n{client_email}"]')
    lines.append(f'P4["☁️ Service Type\\n{service_type}"]')
    lines.append(f'P5["🎯 Attacks\\n{q(attack_summary)}"]')

    lines.append("P1 --> P2 --> P3 --> P4 --> P5")
    lines.append("end")
    lines.append("")
    lines.append("S3 --> P1")
    lines.append("")

    for node in ["P1", "P2", "P3", "P4", "P5"]:
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
        lines.append(f'{node}["📦 ECR Image\\n{q(short_repo)}"]')
        lines.append(f"style {node} fill:#fff1f2,stroke:#e11d48,stroke-width:1px,color:#0f172a")

    lines.append("end")
    lines.append("")
    return repo_nodes


def attack_block(lines, payload, target_ec2_nodes, suricata_nodes):
    attacks = payload.get("attacks", [])
    if not attacks:
        return

    lines.append("subgraph ATTACK_SIM [Attack Simulation - Kali Linux EC2]")
    lines.append("direction TB")
    lines.append('KALI["🐉 Kali Linux EC2\\nAttack dispatcher"]')
    lines.append("style KALI fill:#fee2e2,stroke:#dc2626,stroke-width:1px,color:#0f172a")

    for idx, attack in enumerate(attacks, start=1):
        tool = safe(attack.get("tool", "attack"))
        attack_type = safe(attack.get("type", "attack"))
        atk_node = f"ATK_{idx}"

        lines.append(f'{atk_node}["🔎 {q(tool)}\\n{q(attack_type)}"]')
        lines.append(f"KALI --> {atk_node}")
        lines.append(f"style {atk_node} fill:#fff1f2,stroke:#fb7185,stroke-width:1px,color:#0f172a")

        for ec2 in target_ec2_nodes:
            lines.append(f"{atk_node} -->|traffic| {ec2}")

        for sur in suricata_nodes:
            lines.append(f"{atk_node} -.->|detection| {sur}")

    lines.append("end")
    lines.append("")


def ec2_block(lines, payload, repo_nodes):
    state = {
        "ec2_nodes": [],
        "suricata_nodes": [],
        "elk_nodes": [],
        "kibana_nodes": [],
        "tool_nodes": [],
        "docker_nodes": [],
    }

    lines.append("subgraph AWS_EC2 [AWS EC2 Lab]")
    lines.append("direction TB")

    for key, inst in payload.get("instances", {}).items():
        node_key = slug(key)
        node_id = f"EC2_{node_key}"

        state["ec2_nodes"].append(node_id)

        instance_name = q(inst.get("name", "Unnamed"))
        instance_type = q(inst.get("instance_type", "unknown"))
        ami = q(inst.get("ami", "unknown"))
        subnet_id = q(inst.get("subnet_id", "unknown"))
        security_groups = ", ".join(q(x) for x in inst.get("security_groups", [])) or "none"

        lines.append(f"subgraph {node_id}_BOX [Instance: {instance_name}]")
        lines.append("direction TB")

        lines.append(f'{node_id}["🖥️ EC2 Instance\\n{instance_name}\\nType: {instance_type}\\nAMI: {ami}"]')
        lines.append(f"ANS --> {node_id}")
        lines.append(f"style {node_id} fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a")

        subnet_node = f"{node_id}_SUBNET"
        sg_node = f"{node_id}_SG"
        runtime_node = f"{node_id}_DOCKER"

        state["docker_nodes"].append(runtime_node)

        lines.append(f'{subnet_node}["🌐 Subnet\\n{subnet_id}"]')
        lines.append(f'{sg_node}["🔐 Security Groups\\n{security_groups}"]')
        lines.append(f'{runtime_node}["🐳 Docker Runtime"]')

        lines.append(f"style {subnet_node} fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a")
        lines.append(f"style {sg_node} fill:#eef2ff,stroke:#6366f1,stroke-width:1px,color:#0f172a")
        lines.append(f"style {runtime_node} fill:#e0f2fe,stroke:#0284c7,stroke-width:1px,color:#0f172a")

        lines.append(f"{subnet_node} --> {node_id}")
        lines.append(f"{sg_node} --> {node_id}")
        lines.append(f"{node_id} --> {runtime_node}")

        tools = inst.get("tools_to_install", [])
        for idx, tool in enumerate(tools, start=1):
            tool_name = safe(tool.get("name", "unknown"))
            repo = safe(tool.get("ecr_repo_url", "")).strip()
            tag = safe(tool.get("image_tag", "latest"))
            run_args = safe(tool.get("run_args", ""))

            tool_node = f"{node_id}_TOOL_{idx}"
            tool_name_l = tool_name.lower()
            state["tool_nodes"].append(tool_node)

            if "suricata" in tool_name_l:
                state["suricata_nodes"].append(tool_node)
            if tool_name_l in {"elk", "logstash", "kibana"} or "elk" in tool_name_l:
                state["elk_nodes"].append(tool_node)

            image_name = repo.split("/")[-1] if repo else "n/a"
            lines.append(
                f'{tool_node}["{icon_for_tool(tool_name)} {q(tool_name)}\\n'
                f'Image: {q(image_name)}:{q(tag)}\\n'
                f'Args: {q(short(run_args, 72))}"]'
            )
            lines.append(f"{runtime_node} --> {tool_node}")
            lines.append(f"style {tool_node} fill:#cffafe,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

            if repo and repo in repo_nodes:
                lines.append(f"{repo_nodes[repo]} --> {runtime_node}")

        sur_node = next((n for n in state["tool_nodes"] if "TOOL" in n), None)
        if len(tools) >= 2:
            suricata_node = next((n for n, t in zip(state["tool_nodes"][-len(tools):], tools)
                                  if "suricata" in safe(t.get("name", "")).lower()), None)
            elk_node = next((n for n, t in zip(state["tool_nodes"][-len(tools):], tools)
                             if safe(t.get("name", "")).lower() in {"elk", "logstash", "kibana"} or "elk" in safe(t.get("name", "")).lower()), None)
            if suricata_node and elk_node:
                lines.append(f"{suricata_node} -->|alerts / logs| {elk_node}")

        lines.append("end")
        lines.append("")

    lines.append("end")
    lines.append("")
    return state


def observability_block(lines, state):
    if not state["suricata_nodes"] and not state["elk_nodes"]:
        return

    lines.append("subgraph OBS [Observability]")
    lines.append("direction LR")
    lines.append('OBS_LOGS["📡 Alerts / Logs Stream"]')
    lines.append('OBS_DASH["📈 Kibana Dashboard"]')
    lines.append("style OBS_LOGS fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")
    lines.append("style OBS_DASH fill:#ecfeff,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

    if state["suricata_nodes"]:
        lines.append(f"{state['suricata_nodes'][0]} --> OBS_LOGS")
    if state["elk_nodes"]:
        lines.append(f"{state['elk_nodes'][0]} --> OBS_DASH")

    lines.append("OBS_LOGS --> OBS_DASH")
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
    state = ec2_block(lines, payload, repo_nodes)
    attack_block(lines, payload, state["ec2_nodes"], state["suricata_nodes"])
    observability_block(lines, state)
    outputs_block(lines)
    footer(lines)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("[OK] Mermaid diagram generated")


if __name__ == "__main__":
    main()
