#!/usr/bin/env bash
set -euo pipefail

LAB_ID="${1:?lab id required}"
KALI_HOST="${2:?kali host required}"
KALI_USER="${3:?kali user required}"
SSH_KEY="${4:?ssh key file required}"
DEST_DIR="${5:-artifacts}"

mkdir -p "$DEST_DIR"

scp -i "$SSH_KEY" -o StrictHostKeyChecking=no -r \
  "${KALI_USER}@${KALI_HOST}:/home/kali/security-validation/reports/${LAB_ID}" \
  "${DEST_DIR}/"
