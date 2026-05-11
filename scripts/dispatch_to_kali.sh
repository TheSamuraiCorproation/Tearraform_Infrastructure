#!/usr/bin/env bash
set -euo pipefail

REQUEST_JSON="${1:?request json required}"
KALI_HOST="${2:?kali host required}"
KALI_USER="${3:?kali user required}"
SSH_KEY="${4:?ssh key file required}"

LAB_ID="$(jq -r '.lab_id' "$REQUEST_JSON")"
REMOTE_BASE="/home/kali/security-validation"
REMOTE_REQ="${REMOTE_BASE}/incoming/${LAB_ID}.json"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "$REQUEST_JSON" \
  "${KALI_USER}@${KALI_HOST}:${REMOTE_REQ}"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no \
  "${KALI_USER}@${KALI_HOST}" \
  "bash ${REMOTE_BASE}/dispatcher.sh ${REMOTE_REQ}"
