# 設定・デプロイ設計

## 設定ファイル（`config.py`）

| 設定項目 | デフォルト値 | 環境変数 |
|---------|------------|---------|
| LM Studio ホスト | `host.docker.internal` | `LM_STUDIO_HOST` |
| LM Studio ポート | `1234` | `LM_STUDIO_PORT` |
| 使用モデル | `qwen2.5-7b-instruct` | `LM_STUDIO_MODEL` |
| LM Studio API URL | `http://{HOST}:{PORT}/v1/chat/completions` | — |
| 出力ファイルサフィックス | `_masked` | — |
| リクエストタイムアウト | `120` 秒 | — |
| 対応拡張子 | `.xlsx`, `.pptx`, `.docx` | — |

---

## ローカル設定オーバーライド

`config.local.py` を作成することでデフォルト設定を上書きできる（`.gitignore` 対象）。

```python
# config.local.py の例
LM_STUDIO_HOST = "192.168.1.100"
LM_STUDIO_PORT = 5678
DEFAULT_MODEL  = "llama-3.1-8b-instruct"
```

---

## Docker デプロイ手順

### 前提条件

- Docker Desktop インストール済み
- LM Studio インストール済み・モデルロード済み（ポート 1234 で待機）

### ビルドと起動

```bash
# イメージビルド（初回のみ、GiNZA モデルのダウンロードを含む）
docker compose build

# バックグラウンドで起動
docker compose up -d

# ブラウザでアクセス
open http://localhost:8501
```

### 停止

```bash
docker compose down
```

---

## ボリュームマウント

| コンテナパス | ホストパス | 用途 |
|------------|----------|------|
| `/data` | `${HOME}/Documents` | 処理対象ファイルへのアクセス |

UI でのフォルダ指定例:

| ホストパス | コンテナ内パス |
|----------|--------------|
| `~/Documents/reports/` | `/data/reports/` |
| `~/Documents/hr/2024/` | `/data/hr/2024/` |

---

## MCP サーバーの設定（Claude Desktop 連携）

`claude_desktop_config.json` に以下を追記する。

```json
{
  "mcpServers": {
    "pii-masker": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "${HOME}/Documents:/data",
        "pii-masker",
        "python", "main.py", "--mode", "mcp"
      ]
    }
  }
}
```

---

## ネットワークセキュリティ

| 通信経路 | タイミング | PII 含む？ |
|---------|----------|-----------|
| Docker Hub | ビルド時のみ | なし |
| PyPI | ビルド時のみ | なし |
| Hugging Face | ビルド時のみ（モデル取得） | なし |
| host.docker.internal:1234 | 処理実行時 | あり（ローカルのみ） |

**処理実行中に PII がホスト外へ送信されることはない。**
