#!/usr/bin/env bash
set -euo pipefail

INSTANCE_ID="${1:?instance id required}"
REGION="${2:-eu-central-1}"
TARGET_IP="${3:?target ip required}"

echo "[+] Waiting for EC2 status checks..."
aws ec2 wait instance-status-ok --instance-ids "$INSTANCE_ID" --region "$REGION"

echo "[+] Waiting for SSH on $TARGET_IP ..."
for i in $(seq 1 60); do
  if ssh -o BatchMode=yes -o ConnectTimeout=5 ubuntu@"$TARGET_IP" 'echo READY' >/dev/null 2>&1; then
    echo "[+] Lab is reachable"
    exit 0
  fi
  sleep 10
done

echo "[!] Lab did not become reachable in time" >&2
exit 1
