#!/bin/bash
# PII Masker インストーラー（ダブルクリックで実行）
# Mac 非エンジニア向け: Docker イメージのビルドと Claude Desktop MCP 設定を自動化

set -e
cd "$(dirname "$0")"

echo "======================================"
echo " PII Masker インストーラー"
echo "======================================"
echo ""

# 1. Docker Desktop チェック
echo "[1/4] Docker Desktop を確認中..."
if ! command -v docker >/dev/null 2>&1; then
  echo ""
  echo "  ✗ Docker Desktop が見つかりません。"
  echo "  ダウンロードページを開きます..."
  open "https://www.docker.com/products/docker-desktop/"
  echo ""
  echo "  Docker Desktop をインストール・起動してから、再度このファイルをダブルクリックしてください。"
  read -p "  Enter キーで終了..."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "  ✗ Docker は起動していません。Docker Desktop を起動します..."
  open -a "Docker"
  echo "  Docker Desktop の起動を待っています（最大 60 秒）..."
  for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  if ! docker info >/dev/null 2>&1; then
    echo "  ✗ Docker の起動を確認できませんでした。起動後に再実行してください。"
    read -p "  Enter キーで終了..."
    exit 1
  fi
fi
echo "  ✓ Docker Desktop OK"
echo ""

# 2. LM Studio チェック（任意）
echo "[2/4] LM Studio を確認中..."
if [ -d "/Applications/LM Studio.app" ]; then
  echo "  ✓ LM Studio インストール済み"
else
  echo "  ! LM Studio が見つかりません。ダウンロードページを開きます..."
  open "https://lmstudio.ai/"
  echo "  （LM Studio でモデルをダウンロードし、Local Server を起動してください）"
fi
echo ""

# 3. Docker イメージをビルド
echo "[3/4] PII Masker の Docker イメージをビルド中..."
echo "  ※ 初回は 5〜10 分ほどかかります（GiNZA モデル ~500MB を含む）"
echo ""
docker compose build
echo "  ✓ ビルド完了"
echo ""

# 4. Claude Desktop MCP 設定（任意）
echo "[4/4] Claude Desktop の MCP 設定..."
CLAUDE_CONFIG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

if [ -d "$HOME/Library/Application Support/Claude" ]; then
  read -p "  Claude Desktop に PII Masker を MCP ツールとして登録しますか？ [y/N]: " ANS
  if [[ "$ANS" =~ ^[Yy]$ ]]; then
    mkdir -p "$(dirname "$CLAUDE_CONFIG")"

    # 既存 config をバックアップ
    if [ -f "$CLAUDE_CONFIG" ]; then
      cp "$CLAUDE_CONFIG" "${CLAUDE_CONFIG}.backup.$(date +%Y%m%d%H%M%S)"
      echo "  ✓ 既存設定をバックアップしました"
    fi

    # Python で安全に JSON マージ
    /usr/bin/python3 - "$CLAUDE_CONFIG" "$HOME/Documents" <<'PYEOF'
import json, sys, os
path, docs = sys.argv[1], sys.argv[2]
cfg = {}
if os.path.exists(path):
    try:
        with open(path) as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}
cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["pii-masker"] = {
    "command": "docker",
    "args": [
        "run", "--rm", "-i",
        "--add-host=host.docker.internal:host-gateway",
        "-v", f"{docs}:/data",
        "pii-masker",
        "--mode", "mcp"
    ]
}
with open(path, "w") as f:
    json.dump(cfg, f, indent=2, ensure_ascii=False)
print(f"  ✓ {path} に pii-masker を登録しました")
PYEOF
    echo "  → Claude Desktop を再起動してください"
  else
    echo "  スキップしました（後から再実行できます）"
  fi
else
  echo "  ! Claude Desktop 未インストールのためスキップ"
fi

echo ""
echo "======================================"
echo " インストール完了"
echo "======================================"
echo ""
echo " 使い方:"
echo "   ・GUI で使う → start.command をダブルクリック"
echo "   ・Claude Desktop で使う → Claude を再起動"
echo ""
read -p " Enter キーで終了..."
