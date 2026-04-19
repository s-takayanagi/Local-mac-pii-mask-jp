#!/bin/bash
# PII Masker 停止

set -e
cd "$(dirname "$0")"

echo "PII Masker を停止中..."
docker compose down
echo "✓ 停止しました"
echo ""
read -p "Enter キーで終了..."
