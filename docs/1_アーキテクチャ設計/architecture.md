# アーキテクチャ設計

## コンポーネント構成

```
pii-masker/
├── core/               # マスキングパイプライン
│   ├── layer1_regex.py     # Layer 1: 正規表現マッチング
│   ├── layer2_ner.py       # Layer 2: NER（固有表現認識）
│   ├── layer3_llm.py       # Layer 3/4: LLM マスキング & レビュー
│   └── pipeline.py         # パイプライン統括
├── file_handlers/      # ファイル形式別処理
│   ├── base.py             # 基底プロトコル
│   ├── xlsx_handler.py     # Excel
│   ├── pptx_handler.py     # PowerPoint
│   └── docx_handler.py     # Word
├── ui/                 # ユーザーインターフェース
│   └── streamlit_app.py    # Streamlit Web UI
├── mcp/                # MCP サーバー
│   └── server.py           # FastMCP（Claude Desktop 連携）
├── main.py             # エントリーポイント
├── config.py           # 設定
└── models.py           # データモデル
```

---

## 実行モード

`main.py` は 3 つのモードをサポートする。

| モード | 起動コマンド | 用途 |
|--------|------------|------|
| UI | `python main.py --mode ui` | Streamlit Web GUI（デフォルト） |
| MCP | `python main.py --mode mcp` | Claude Desktop 向け MCP サーバー（stdio） |
| CLI | `python main.py --mode cli --folder <path>` | バッチ処理 |

---

## 依存コンポーネント間の通信

```
Streamlit UI (8501)
        │
        ▼
   pipeline.py
   ┌─────────────────────────────┐
   │  Layer1 → Layer2 → Layer3 → Layer4 │
   └─────────────────────────────┘
        │                       │
        │ NER                   │ LLM API
        ▼                       ▼
 ja_ginza_electra        LM Studio API
 (コンテナ内蔵)          host.docker.internal:1234
```

**外部通信は LM Studio API のみ**（PII を含むテキストはホスト外へ出ない）

---

## Docker 構成

### Dockerfile 概要

- ベースイメージ: `python:3.11-slim`
- パッケージマネージャー: `uv`（高速インストール）
- NER モデル `ja_ginza_electra` をビルド時にダウンロード・内蔵
- 公開ポート: `8501`（Streamlit）
- デフォルト起動: `python main.py --mode ui`

### docker-compose.yml 概要

| 設定項目 | 値 |
|---------|---|
| サービス名 | `pii-masker-ui` |
| ポートマッピング | `8501:8501` |
| ボリューム | `${HOME}/Documents:/data:rw` |
| 再起動ポリシー | `unless-stopped` |
| LM_STUDIO_HOST | `host.docker.internal` |
| LM_STUDIO_PORT | `1234` |
