# PII Masker

日本語文書（.xlsx / .pptx / .docx）の個人情報をローカル環境で一括マスキングするツールです。  
PIIはクラウドに一切送信されません。LM Studio 上のローカル LLM（推奨: Gemma-4 E4B / その他動作確認済み: Qwen3 1.7B / LFM2-350M-PII-Extract-JP）が処理します。

```
[社内文書（PII含む）]
        ↓
  PII Masker（完全ローカル・オフライン）
  ※ Python / GiNZA / 全依存は Docker 内で完結
        ↓
[マスキング済み文書]
        ↓
  Claude（Cowork / Code / chat）で安全に利用
```

---

## Mac にインストールするもの（これだけ）

| ツール | 用途 | 備考 |
|--------|------|------|
| [Docker Desktop](https://www.docker.com/products/docker-desktop/) | Python・GiNZA・アプリ実行環境 | Python のローカルインストール不要 |
| [LM Studio](https://lmstudio.ai/) | ローカル LLM の推論（推奨: Gemma-4 E4B） | 完全オフライン |
| [Claude Desktop](https://claude.ai/download) | MCPツールとして呼び出す | 任意 |

Python・pip・uv・GiNZA などは **すべて Docker イメージ内に封じ込まれます**。

---

## アーキテクチャ

マスキングは4層パイプラインで処理されます：

| レイヤー | 手法 | 対象 |
|---------|------|------|
| Layer1 | 正規表現 | 電話番号・メール・郵便番号・URL・マイナンバー・住所（都道府県+番地） |
| Layer2 | GiNZA NER（ja_ginza_electra） | 氏名・住所・会社名 |
| Layer3 | LLM Masker（任意モデル） | 文脈依存の残存PII |
| Layer4 | LLM Reviewer（任意モデル） | 見落とし検出・過検出修正・追加マスク |

```
Mac ホスト
├── Docker Desktop
│   └── pii-masker コンテナ
│       ├── Python 3.11
│       ├── GiNZA / spaCy（モデル込み）
│       ├── Streamlit UI  → localhost:8501
│       └── MCP Server    → stdio（Claude Desktop から呼び出し）
└── LM Studio  → localhost:1234
    └── Gemma-4 E4B（推奨） / Qwen3 1.7B / LFM2-350M-PII-Extract-JP 等
```

コンテナ内から LM Studio には `host.docker.internal:1234` で接続します。

---

## かんたん導入（非エンジニア向け・Mac）

ターミナル操作や JSON 編集は不要です。

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) をインストール・起動
2. [LM Studio](https://lmstudio.ai/) をインストールし、モデル（推奨: `google/gemma-4-e4b`）をダウンロード → Local Server を起動
3. このリポジトリを ZIP ダウンロード → 解凍
4. **`install.command` をダブルクリック**（初回のみ・Docker イメージをビルド。5〜10分）
   - 「開発元を確認できないため開けません」と出たら、Finder で右クリック → 「開く」
5. **`start.command` をダブルクリック**（ブラウザで UI が開きます）
6. 停止するときは **`stop.command`**

Claude Desktop 連携（MCP）を使う場合は `install.command` 実行時に y と入力すると自動設定されます。

---

### .dmg で配布する（社内展開向け）

配布担当者が `.dmg` を作成し、エンドユーザーに渡す運用も可能です。

```bash
# 署名なし（Gatekeeper 警告は右クリック→開くで回避可能）
bash build/make_dmg.sh

# 署名あり（Apple Developer Program 加入時）
DEVELOPER_ID="Developer ID Application: Your Name (XXXXXXXXXX)" bash build/make_dmg.sh
```

`dist/PII-Masker.dmg` が生成されます。エンドユーザーは:

1. `.dmg` をダブルクリック
2. 「PII Masker」フォルダを **Applications** にドラッグ
3. `/Applications/PII Masker/Install PII Masker.app` を右クリック → 「開く」（初回のみ）
4. 以降は `Start PII Masker.app` / `Stop PII Masker.app` をダブルクリック

---

## セットアップ（手動）

### 1. LM Studio の準備

1. LM Studio を起動
2. 以下のいずれかのモデルをダウンロード（手動テスト済み）
   - `google/gemma-4-e4b`（**推奨・品質重視**・汎用 LLM モード）
   - `qwen/qwen3-1.7b`（汎用 LLM モード・軽量）
   - `LFM2-350M-PII-Extract-JP`（LFM2 専用モード・約 400MB・**高速重視**）

   ※ 各モデルの検出件数・処理時間の比較は [docs/3_設定・開発/manual_test_results.md](docs/3_設定・開発/manual_test_results.md) を参照。
3. 「Local Server」タブでサーバーを起動（デフォルトポート: 1234）

### 2. Docker イメージのビルド

```bash
git clone https://github.com/your-org/pii-masker.git
cd pii-masker

# 初回のみ（GiNZA モデル ~500MB を含むため数分かかります）
bash build/build_docker.sh
```

以降はオフラインで動作します。

---

## 使い方

### GUI（Streamlit）

```bash
docker compose up
```

ブラウザで `http://localhost:8501` を開きます。

1. サイドバーで LM Studio 接続を確認
2. モデルを選択（LFM2-350M-PII-Extract-JP を選択すると専用モードで動作）
3. 処理レイヤー（Layer 1〜4）のON/OFFを設定
4. マスキングから除外したいPII種別をチェックボックスで選択
5. 処理フォルダを入力（コンテナ内では `/data/` 以下にマウントされています）
6. 「マスキング開始」をクリック

**フォルダのマウント設定（docker-compose.yml）**:

```yaml
volumes:
  - "${HOME}/Documents:/data:rw"
```

`~/Documents/` 以下のファイルを `/data/xxx/yyy.xlsx` として指定できます。  
必要に応じて `docker-compose.yml` のマウントパスを変更してください。

### CLI

```bash
docker run --rm \
  -v "${HOME}/Documents:/data" \
  pii-masker --mode cli --folder /data/your-folder
```

### MCP サーバー（Claude Desktop 連携）

`~/Library/Application Support/Claude/claude_desktop_config.json` に追加：

```json
{
  "mcpServers": {
    "pii-masker": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--add-host=host.docker.internal:host-gateway",
        "-v", "/Users/your-name/Documents:/data",
        "pii-masker",
        "--mode", "mcp"
      ]
    }
  }
}
```

Claude Desktop を再起動すると `mask_text` / `mask_file` / `mask_folder` ツールが利用可能になります。

> **注意**: `your-name` を実際のユーザー名に変更してください。  
> `docker run --rm -i` は Claude Desktop がプロセスを終了すると自動でコンテナも停止します。

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
| マイナンバー等12桁 | `[識別番号]` |
| URL | `[URL]` |
| その他個人情報 | `[個人情報]` |

---

## テスト

### 実行方法

```bash
# Docker コンテナ内で全テスト実行
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest pytest-cov && python -m pytest tests/ -v"

# カバレッジレポート付き
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest pytest-cov && python -m pytest tests/ -v --cov=core --cov-report=term-missing"
```

### テスト構成（122 tests）

| ファイル | テスト数 | 対象 |
|---------|---------|------|
| `tests/test_layer1_regex.py` | 18 | Layer 1 正規表現パターン |
| `tests/test_layer2_ner.py` | 19 | Layer 2 NER（spaCy モック） |
| `tests/test_layer3_llm.py` | 23 | Layer 3/4 LLM・LFM2モード（requests モック） |
| `tests/test_pipeline.py` | 13 | マスキングパイプライン統合 |
| `tests/test_file_handlers.py` | 22 | xlsx / pptx / docx ハンドラー |
| `tests/test_ui.py` | 15 | Streamlit UI・ヘルパー関数 |

### テスト設計方針

- **Layer 2 (NER)**: `ja_ginza_electra` モデルを `unittest.mock` でモック。CI/CD 環境でモデル不要。
- **Layer 3/4 (LLM)**: `requests.post` をモックし、接続エラー・タイムアウト・不正JSONを網羅。
- **ファイルハンドラー**: `tmp_path` フィクスチャで実ファイルを生成し、`mask_text` をモック。
- **UI**: `streamlit.testing.v1.AppTest` で LM Studio 接続チェック・ボタン状態を検証。

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

## 環境変数

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `LM_STUDIO_HOST` | `host.docker.internal` | LM Studio のホスト名 |
| `LM_STUDIO_PORT` | `1234` | LM Studio のポート番号 |
| `LM_STUDIO_MODEL` | `google/gemma-4-e4b` | 使用するモデル名（LM Studio のモデル ID と一致させる）。推奨: `google/gemma-4-e4b`。その他動作確認済み: `qwen/qwen3-1.7b` / `LFM2-350M-PII-Extract-JP` |

---

## ビルド

```bash
# arm64（M1/M2 Mac）向けビルド
bash build/build_docker.sh

# タグ指定
bash build/build_docker.sh v1.0.0
```

---

## メモリ要件（M1 16GB）

| コンポーネント | 使用量 |
|---------------|--------|
| OS + 業務アプリ | ~4GB |
| LM Studio 本体 | ~0.5GB |
| LLM モデル（推奨: Gemma-4 E4B） | ~0.4〜4GB |
| GiNZA ja_ginza_electra | ~1.5GB |
| PII Masker コンテナ | ~0.5GB |
| **合計** | **~7〜10GB** |

---

## 通信範囲

| 通信先 | タイミング | 内容 |
|--------|-----------|------|
| `host.docker.internal:1234` | マスキング処理時 | LM Studio API（テキスト推論）|
| Docker Hub / PyPI / Hugging Face | `docker build` 時のみ | ライブラリ・モデル取得 |
| **外部（処理中）** | **なし** | **PIIは一切外部に出ない** |

---

## ライセンス

MIT

### 使用コンポーネント

| コンポーネント | ライセンス | 備考 |
|---|---|---|
| Gemma-4 E4B | Gemma Terms of Use | **推奨モデル**。動作確認済み・汎用 LLM モード |
| Qwen3 1.7B | Apache 2.0 | 動作確認済み。軽量な汎用 LLM モード |
| LFM2-350M-PII-Extract-JP | LFM Open License v1.0 | 動作確認済み。特化型モードで対応。商用利用は売上 $10M 以上の場合は要ライセンス確認 |
| GiNZA v5 + ja_ginza_electra | MIT | |
| spaCy | MIT | |
| openpyxl | MIT | |
| python-pptx | MIT | |
| python-docx | MIT | |
| Streamlit | Apache 2.0 | |
| FastMCP | Apache 2.0 | |
| requests | Apache 2.0 | |
