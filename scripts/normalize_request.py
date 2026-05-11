#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path

TYPE_TO_SCENARIO = {
    "ai": "app-check",
    "os": "host-check",
    "network": "network-check",
    "web": "web-check",
}

def safe_name(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9._-]+", "-", value)
    return value.strip("-")

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--target-ip", required=True)
    parser.add_argument("--lab-id", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))

    required = ["file_name", "user_name", "client_email", "service_type", "instances"]
    for key in required:
        if key not in payload:
            print(f"Missing required field: {key}", file=sys.stderr)
            return 2

    raw_items = payload.get("attacks", [])
    scenarios = []
    seen = set()

    for item in raw_items:
        attack_type = item.get("type")
        if attack_type not in TYPE_TO_SCENARIO:
            print(f"Unsupported requested type: {attack_type}", file=sys.stderr)
            return 3

        scenario = TYPE_TO_SCENARIO[attack_type]
        if scenario not in seen:
            scenarios.append(scenario)
            seen.add(scenario)

    if not scenarios:
        print("No valid scenarios found in request", file=sys.stderr)
        return 4

    normalized = {
        "lab_id": args.lab_id,
        "file_name": safe_name(payload["file_name"]),
        "user_name": payload["user_name"],
        "client_email": payload["client_email"],
        "service_type": payload["service_type"],
        "target_ip": args.target_ip,
        "validation_scenarios": scenarios
    }

    Path(args.output).write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Normalized request written to {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
