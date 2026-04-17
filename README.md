# PII Masker

日本語文書（.xlsx / .pptx / .docx）の個人情報をローカル環境で一括マスキングするツールです。  
PIIはクラウドに一切送信されません。LM Studio 上の Qwen2.5-7B がローカルで処理します。

```
[社内文書（PII含む）]
        ↓
  PII Masker（完全ローカル・オフライン）
        ↓
[マスキング済み文書]
        ↓
  Claude（Cowork / Code / chat）で安全に利用
```

---

## アーキテクチャ

マスキングは3層パイプラインで処理されます：

| レイヤー | 手法 | 対象 |
|---------|------|------|
| Layer1 | 正規表現 | 電話番号・メール・郵便番号・マイナンバー等 |
| Layer2 | GiNZA NER（ja_ginza_electra） | 氏名・住所・会社名 |
| Layer3 | LLM Masker（Qwen2.5-7B） | 文脈依存の残存PII |
| Layer4 | LLM Reviewer（Qwen2.5-7B） | 見落とし検出・追加マスク |

---

## 前提条件

- macOS（Apple Silicon M1 推奨）
- [LM Studio](https://lmstudio.ai/) をインストール済み
- LM Studio で `Qwen2.5-7B-Instruct`（Q4_K_M、約5GB）をダウンロード・起動済み
- Python 3.11 〜 3.12
- [uv](https://github.com/astral-sh/uv) （パッケージ管理）

### LM Studio セットアップ

1. LM Studio を起動
2. `Qwen2.5-7B-Instruct`（Q4_K_M）をダウンロード
3. 「Local Server」タブでサーバーを起動（デフォルトポート: 1234）
4. `http://localhost:1234/v1/models` にアクセスしてモデル名を確認

---

## インストール

```bash
# リポジトリをクローン
git clone https://github.com/your-org/pii-masker.git
cd pii-masker

# 依存関係をインストール
uv sync

# GiNZA モデルのダウンロード（初回のみ・要ネット接続）
uv run python -m spacy download ja_ginza_electra
```

---

## 使い方

### GUI（Streamlit アプリ）

```bash
uv run streamlit run ui/streamlit_app.py
# または
uv run python main.py --mode ui
```

ブラウザで `http://localhost:8501` が開きます。

1. サイドバーで LM Studio 接続を確認
2. モデルを選択
3. 処理フォルダを入力
4. 「マスキング開始」をクリック

### CLI

```bash
uv run python main.py --mode cli --folder /path/to/folder
```

### MCP サーバー（Claude Desktop 連携）

```bash
uv run python main.py --mode mcp
```

`~/Library/Application Support/Claude/claude_desktop_config.json` に以下を追加：

```json
{
  "mcpServers": {
    "pii-masker": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/pii-masker",
        "run",
        "main.py",
        "--mode",
        "mcp"
      ]
    }
  }
}
```

Claude Desktop を再起動すると、`mask_text` / `mask_file` / `mask_folder` ツールが利用可能になります。

---

## 出力仕様

| 入力ファイル | 出力ファイル |
|-------------|-------------|
| `report.xlsx` | `report_masked.xlsx` |
| `slide.pptx` | `slide_masked.pptx` |
| `contract.docx` | `contract_masked.docx` |

元ファイルは上書きされません。

### マスキングタグ一覧

| 置換対象 | タグ |
|---------|------|
| 氏名 | `[氏名]` |
| 住所 | `[住所]` |
| 電話番号 | `[電話番号]` |
| メールアドレス | `[メール]` |
| 会社名・組織名 | `[会社名]` |
| 郵便番号 | `[郵便番号]` |
| 生年月日 | `[生年月日]` |
| マイナンバー等12桁 | `[識別番号]` |
| URL | `[URL]` |
| その他個人情報 | `[個人情報]` |

---

## テスト

```bash
uv run pytest tests/ -v
```

### テスト用サンプルデータ

```
山田太郎,yamada.taro@example.com,090-1234-5678,東京都渋谷区1-2-3
田中花子,090-9876-5432,〒150-0001,株式会社テスト
```

期待出力：
```
[氏名],[メール],[電話番号],[住所]
[氏名],[電話番号],[郵便番号],[会社名]
```

---

## ビルド（.app 化）

```bash
bash build/build_app.sh
# 出力: dist/PII Masker.app
```

---

## メモリ要件（M1 16GB）

| コンポーネント | 使用量 |
|---------------|--------|
| OS + 業務アプリ | ~4GB |
| LM Studio 本体 | ~0.5GB |
| Qwen2.5-7B Q4_K_M | ~5GB |
| GiNZA ja_ginza_electra | ~1.5GB |
| PII Masker 本体 | ~0.5GB |
| **合計** | **~11.5GB** |

---

## ライセンス

MIT

### 使用コンポーネント

| コンポーネント | ライセンス |
|---|---|
| Qwen2.5-7B-Instruct | Apache 2.0 |
| GiNZA v5 + ja_ginza_electra | MIT |
| spaCy | MIT |
| openpyxl | MIT |
| python-pptx | MIT |
| python-docx | MIT |
| Streamlit | Apache 2.0 |
| FastMCP | Apache 2.0 |
| requests | Apache 2.0 |

---

## 注意事項

- GiNZA モデルは初回起動時にインターネット経由でダウンロードされます（`~/.cache/pii_masker/ginza/`）
- マスキング処理中の外部通信は `localhost:1234`（LM Studio）のみです
- LM Studio のポート 1234 への外部アクセスはファイアウォールでブロックすることを推奨します
- Codestral（Mistral Non-Production License）および DeepSeek R1/V3 は本プロジェクトでは使用しません
