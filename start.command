#!/bin/bash
# PII Masker 起動（ダブルクリックで GUI を開く）

set -e
cd "$(dirname "$0")"

echo "======================================"
echo " PII Masker を起動中..."
echo "======================================"
echo ""

# Docker 起動チェック
if ! docker info >/dev/null 2>&1; then
  echo "Docker Desktop が起動していません。起動します..."
  open -a "Docker"
  for i in {1..30}; do
    if docker info >/dev/null 2>&1; then break; fi
    sleep 2
  done
  if ! docker info >/dev/null 2>&1; then
    echo "✗ Docker の起動を確認できませんでした。"
    read -p "Enter キーで終了..."
    exit 1
  fi
fi

# LM Studio 接続確認
if ! curl -s --max-time 2 http://localhost:1234/v1/models >/dev/null 2>&1; then
  echo "! LM Studio のローカルサーバー (localhost:1234) に接続できません。"
  echo "  LM Studio を起動し、Local Server タブでサーバーを Start してください。"
  echo ""
fi

# UI をバックグラウンドで起動
echo "コンテナを起動中..."
docker compose up -d pii-masker-ui

# ブラウザが開けるまで待機
echo "UI の起動を待っています..."
for i in {1..30}; do
  if curl -s --max-time 1 http://localhost:8501 >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo ""
echo "✓ ブラウザで http://localhost:8501 を開きます"
open "http://localhost:8501"
echo ""
echo " 停止するには stop.command をダブルクリックしてください。"
echo ""
read -p " Enter キーでこのウィンドウを閉じる..."
