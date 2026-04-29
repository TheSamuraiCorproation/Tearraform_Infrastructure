import json
import argparse
import html
from datetime import datetime, UTC


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    if "wazuh" in n:
        return "🔍"
    if "docker" in n:
        return "🐳"
    return "📦"


# ---------------------------------------------------------------------------
# Mermaid blocks  (unchanged from original)
# ---------------------------------------------------------------------------

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
        f"{safe(a.get('name', 'attack'))} ({safe(a.get('type', '?'))})"
        for a in attacks
    ) or "none"

    lines.append("subgraph PAYLOAD [Deployment Payload]")
    lines.append("direction TB")

    file_name    = q(payload.get("file_name", "n/a"))
    user_name    = q(payload.get("user_name", "n/a"))
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
            # tools_to_install can be strings (simple) or dicts (full spec)
            if isinstance(tool, str):
                tools.append({
                    "instance_key": inst_key,
                    "name": tool,
                    "repo": "",
                    "tag": "n/a",
                    "run_args": ""
                })
            else:
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

    lines.append("subgraph REGISTRY [Container Registry - ECR]")
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
        # use 'name' field (real payload) with fallback to 'tool'
        attack_name = safe(attack.get("name", attack.get("tool", "attack")))
        attack_type = safe(attack.get("type", "attack"))
        atk_node = f"ATK_{idx}"

        lines.append(f'{atk_node}["🔎 {q(attack_name)}\\n{q(attack_type)}"]')
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
        node_id  = f"EC2_{node_key}"

        state["ec2_nodes"].append(node_id)

        instance_name   = q(inst.get("name", "Unnamed"))
        instance_type   = q(inst.get("instance_type", "unknown"))
        ami             = q(inst.get("ami", "unknown"))
        subnet_id       = q(inst.get("subnet_id", "unknown"))
        security_groups = ", ".join(q(x) for x in inst.get("security_groups", [])) or "none"

        lines.append(f"subgraph {node_id}_BOX [Instance: {instance_name}]")
        lines.append("direction TB")

        lines.append(f'{node_id}["🖥️ EC2 Instance\\n{instance_name}\\nType: {instance_type}\\nAMI: {ami}"]')
        lines.append(f"ANS --> {node_id}")
        lines.append(f"style {node_id} fill:#f5f3ff,stroke:#8b5cf6,stroke-width:1px,color:#0f172a")

        subnet_node  = f"{node_id}_SUBNET"
        sg_node      = f"{node_id}_SG"
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
        instance_tool_nodes = []

        for idx, tool in enumerate(tools, start=1):
            # handle both string tools and dict tools
            if isinstance(tool, str):
                tool_name = tool
                repo      = ""
                tag       = "n/a"
                run_args  = ""
            else:
                tool_name = safe(tool.get("name", "unknown"))
                repo      = safe(tool.get("ecr_repo_url", "")).strip()
                tag       = safe(tool.get("image_tag", "latest"))
                run_args  = safe(tool.get("run_args", ""))

            tool_node    = f"{node_id}_TOOL_{idx}"
            tool_name_l  = tool_name.lower()
            state["tool_nodes"].append(tool_node)
            instance_tool_nodes.append((tool_node, tool_name_l))

            if "suricata" in tool_name_l:
                state["suricata_nodes"].append(tool_node)
            if tool_name_l in {"elk", "logstash", "kibana"} or "elk" in tool_name_l:
                state["elk_nodes"].append(tool_node)

            image_name = repo.split("/")[-1] if repo else "n/a"

            if repo:
                label = (
                    f'{icon_for_tool(tool_name)} {q(tool_name)}\\n'
                    f'Image: {q(image_name)}:{q(tag)}\\n'
                    f'Args: {q(short(run_args, 72))}'
                )
            else:
                # simple string tool — no ECR info
                label = f'{icon_for_tool(tool_name)} {q(tool_name)}'

            lines.append(f'{tool_node}["{label}"]')
            lines.append(f"{runtime_node} --> {tool_node}")
            lines.append(f"style {tool_node} fill:#cffafe,stroke:#06b6d4,stroke-width:1px,color:#0f172a")

            if repo and repo in repo_nodes:
                lines.append(f"{repo_nodes[repo]} --> {runtime_node}")

        # draw suricata → elk alert edge if both exist on this instance
        suricata_node = next(
            (n for n, l in instance_tool_nodes if "suricata" in l), None
        )
        elk_node = next(
            (n for n, l in instance_tool_nodes
             if l in {"elk", "logstash", "kibana"} or "elk" in l), None
        )
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


# ---------------------------------------------------------------------------
# NEW: HTML wrapper
# Reads the finished .mmd file and wraps it in a self-contained HTML page
# that uses the Mermaid CDN renderer — no build step required.
# ---------------------------------------------------------------------------

def write_html(mmd_path: str, html_path: str, payload: dict) -> None:
    """
    Read the rendered .mmd file and produce a standalone HTML file.

    Parameters
    ----------
    mmd_path  : path to the already-written lab.mmd
    html_path : destination path for lab.html
    payload   : the original payload dict (used for the page header metadata)
    """
    with open(mmd_path, "r", encoding="utf-8") as f:
        mermaid_content = f.read()

    # Escape for safe insertion inside an HTML <pre> / JS template literal
    escaped = mermaid_content.replace("`", "\\`").replace("$", "\\$")

    file_name    = html.escape(str(payload.get("file_name",    "Lab Architecture")))
    user_name    = html.escape(str(payload.get("user_name",    "N/A")))
    client_email = html.escape(str(payload.get("client_email", "N/A")))
    service_type = html.escape(str(payload.get("service_type", "ec2")).upper())
    num_attacks  = len(payload.get("attacks", []))
    num_instances = len(payload.get("instances", {}))

    tools_set = set()
    for inst in payload.get("instances", {}).values():
        for t in inst.get("tools_to_install", []):
            tools_set.add(t if isinstance(t, str) else t.get("name", "unknown"))
    tools_str = html.escape(", ".join(sorted(tools_set)) or "None")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{file_name} — DOJO Lab Architecture</title>
  <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      background: #f1f5f9;
      color: #0f172a;
      min-height: 100vh;
      padding: 24px 16px 48px;
    }}

    .page {{ max-width: 1600px; margin: 0 auto; display: flex; flex-direction: column; gap: 20px; }}

    /* ── Header ── */
    .header {{
      background: #fff;
      border-radius: 12px;
      padding: 24px 28px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    .header h1 {{ font-size: 22px; font-weight: 700; margin-bottom: 16px; }}
    .meta-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
    }}
    .meta-item {{
      background: #f8fafc;
      border-left: 3px solid #6366f1;
      border-radius: 6px;
      padding: 10px 14px;
    }}
    .meta-item .label {{ font-size: 10px; font-weight: 600; text-transform: uppercase; color: #64748b; margin-bottom: 4px; }}
    .meta-item .value {{ font-size: 13px; word-break: break-all; }}

    /* ── Toolbar ── */
    .toolbar {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .btn {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 9px 18px; border: none; border-radius: 8px; cursor: pointer;
      font-size: 13px; font-weight: 500; transition: background .15s, transform .1s;
    }}
    .btn:active {{ transform: scale(.97); }}
    .btn-primary {{ background: #6366f1; color: #fff; }}
    .btn-primary:hover {{ background: #4f46e5; }}
    .btn-secondary {{ background: #e2e8f0; color: #0f172a; }}
    .btn-secondary:hover {{ background: #cbd5e1; }}

    /* ── Diagram card ── */
    .diagram-card {{
      background: #fff;
      border-radius: 12px;
      padding: 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
      overflow-x: auto;
    }}
    .mermaid {{ display: flex; justify-content: center; }}

    /* ── Legend ── */
    .legend {{
      background: #fff;
      border-radius: 12px;
      padding: 20px 24px;
      box-shadow: 0 1px 4px rgba(0,0,0,.08);
    }}
    .legend h3 {{ font-size: 14px; font-weight: 600; margin-bottom: 12px; }}
    .legend ul {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 6px; }}
    .legend li {{ font-size: 13px; color: #475569; padding-left: 18px; position: relative; }}
    .legend li::before {{ content: "✓"; position: absolute; left: 0; color: #22c55e; font-weight: 700; }}

    /* ── Footer ── */
    .footer {{ text-align: center; font-size: 11px; color: #94a3b8; }}

    @media print {{
      body {{ background: #fff; padding: 0; }}
      .toolbar, .legend {{ display: none; }}
      .diagram-card {{ box-shadow: none; }}
    }}
  </style>
</head>
<body>
<div class="page">

  <!-- Header -->
  <div class="header">
    <h1>🏗️ {file_name}</h1>
    <div class="meta-grid">
      <div class="meta-item"><div class="label">👤 User</div><div class="value">{user_name}</div></div>
      <div class="meta-item"><div class="label">✉️ Email</div><div class="value">{client_email}</div></div>
      <div class="meta-item"><div class="label">☁️ Service</div><div class="value">{service_type}</div></div>
      <div class="meta-item"><div class="label">🖥️ Instances</div><div class="value">{num_instances}</div></div>
      <div class="meta-item"><div class="label">🎯 Attacks</div><div class="value">{num_attacks}</div></div>
      <div class="meta-item"><div class="label">🛠️ Tools</div><div class="value">{tools_str}</div></div>
    </div>
  </div>

  <!-- Toolbar -->
  <div class="toolbar">
    <button class="btn btn-secondary" onclick="window.print()">🖨️ Print / Save as PDF</button>
    <button class="btn btn-secondary" onclick="toggleFullscreen()">⛶ Fullscreen</button>
  </div>

  <!-- Diagram -->
  <div class="diagram-card" id="diagramCard">
    <div class="mermaid" id="diagram">
{mermaid_content}
    </div>
  </div>

  <!-- Legend -->
  <div class="legend">
    <h3>📊 What this diagram shows</h3>
    <ul>
      <li>Deployment pipeline: Client → S3 → Jenkins → Terraform → Ansible</li>
      <li>Payload metadata: lab file, user, email, service type, selected attacks</li>
      <li>AWS EC2 instance: AMI, instance type, subnet, security groups</li>
      <li>Docker runtime and all installed security tools (Suricata, ELK, Wazuh …)</li>
      <li>ECR container registry references and image tags</li>
      <li>Kali Linux attack machine and individual attack flows to target EC2</li>
      <li>Suricata detection links and alert / log flow to the ELK stack</li>
      <li>Observability: log stream → Kibana dashboard</li>
    </ul>
  </div>

  <div class="footer">DOJO Cybersecurity Platform — auto-generated architecture diagram</div>

</div><!-- /page -->

<script>
  mermaid.initialize({{ startOnLoad: true, theme: "base", securityLevel: "loose" }});

  function toggleFullscreen() {{
    const el = document.getElementById("diagramCard");
    if (document.fullscreenElement) {{
      document.exitFullscreen();
    }} else {{
      el.requestFullscreen().catch(() => {{}});
    }}
  }}
</script>
</body>
</html>
"""
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(page)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Generate Mermaid diagram from lab payload")
    parser.add_argument("--payload",   required=True,  help="Path to the input payload JSON")
    parser.add_argument("--out",       required=True,  help="Path to write the .mmd diagram file")
    parser.add_argument("--html-out",  default=None,   help="(Optional) Path to write standalone HTML viewer")
    args = parser.parse_args()

    with open(args.payload, "r", encoding="utf-8") as f:
        payload = json.load(f)

    # Build Mermaid lines
    lines = []
    header(lines)
    payload_block(lines, payload)

    tools      = collect_tools(payload)
    repo_nodes = registry_block(lines, tools)
    state      = ec2_block(lines, payload, repo_nodes)
    attack_block(lines, payload, state["ec2_nodes"], state["suricata_nodes"])
    observability_block(lines, state)
    outputs_block(lines)
    footer(lines)

    # Write .mmd
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[OK] Mermaid diagram written → {args.out}")

    # Write HTML viewer if requested
    if args.html_out:
        write_html(args.out, args.html_out, payload)
        print(f"[OK] HTML viewer written     → {args.html_out}")


if __name__ == "__main__":
    main()
