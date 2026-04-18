# 開発ガイド

## 開発環境セットアップ

```bash
# リポジトリクローン
git clone <repo-url>
cd pii-masker

# 仮想環境作成（uv 使用）
uv venv
source .venv/bin/activate

# 依存インストール（開発用含む）
uv pip install -e ".[dev]"

# GiNZA モデルダウンロード
python -m spacy download ja_ginza_electra
```

---

## プロジェクト依存関係

`pyproject.toml` で管理。

### 本体依存

| パッケージ | 用途 |
|-----------|------|
| `streamlit` | Web UI |
| `fastmcp` | MCP サーバーフレームワーク |
| `openpyxl` | Excel 読み書き |
| `python-pptx` | PowerPoint 読み書き |
| `python-docx` | Word 読み書き |
| `requests` | LM Studio API 呼び出し |
| `GiNZA` | 日本語 NER |
| `spaCy` | NLP フレームワーク |

### 開発用依存

| パッケージ | 用途 |
|-----------|------|
| `pytest` | テストフレームワーク |
| `pytest-cov` | カバレッジ計測 |

---

## テスト

### テスト実行

```bash
# Docker コンテナ内（推奨）
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest pytest-cov && python -m pytest tests/ -v"

# カバレッジ付き
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest pytest-cov && python -m pytest tests/ -v --cov=core --cov-report=term-missing"

# 特定ファイルのみ
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest && python -m pytest tests/test_layer1_regex.py -v"
```

### テスト構成（合計 122 tests）

| ファイル | テスト数 | 対象モジュール |
|---------|---------|--------------|
| `tests/test_layer1_regex.py` | 18 | `core/layer1_regex.py` |
| `tests/test_layer2_ner.py` | 19 | `core/layer2_ner.py` |
| `tests/test_layer3_llm.py` | 23 | `core/layer3_llm.py`（LFM2・`_revert_excluded` 含む） |
| `tests/test_pipeline.py` | 13 | `core/pipeline.py` |
| `tests/test_file_handlers.py` | 22 | `file_handlers/` |
| `tests/test_ui.py` | 15 | `ui/streamlit_app.py` |

### テスト設計方針

#### モック戦略

| レイヤー | モック対象 | 理由 |
|---------|-----------|------|
| Layer 2 (NER) | `core.layer2_ner._load_nlp` | `ja_ginza_electra` モデル不要でCI/CDを軽量化 |
| Layer 3/4 (LLM) | `requests.post` | LM Studio サーバー不要、エラー系を安全に再現 |
| ファイルハンドラー | `file_handlers.*.mask_text` | パイプラインと切り離して I/O 処理のみ検証 |

#### テストカバレッジ範囲

**Layer 1 — 正規表現** (`test_layer1_regex.py`)
- 携帯電話番号（`090-XXXX-XXXX`）・固定電話番号（`03-XXXX-XXXX`）
- 全角ハイフンの電話番号（`090−XXXX−XXXX`）
- メールアドレス（`.co.jp` 形式を含む）・郵便番号（`〒` あり／なし）・URL
- 12桁識別番号（11桁・13桁は非マスク）
- `excluded_tags` による除外・空文字列・複合パターン

**Layer 2 — NER** (`test_layer2_ner.py`)
- `Person`/`PERSON` → `[氏名]`、`Organization`/`Company` → `[会社名]`
- `Address`/`City`/`Province` → `[住所]`
- 都道府県名のみ（行政区画）は非マスク、フル住所はマスク対象
- `@` を含まないエンティティを `[メール]` と誤分類しないこと
- `excluded_tags` による除外・未知ラベルの無視
- `_is_admin_unit()` の単体テスト

**Layer 3/4 — LLM** (`test_layer3_llm.py`)
- 正常レスポンス・`excluded_tags` による revert 処理
- `ConnectionError`・`Timeout`・`HTTPError`・不正 JSON の各エラーハンドリング
- `_revert_excluded()` の単体テスト（`reference_text` による順序保証含む）
- LFM2 モード: `_is_lfm2_model()`・`_apply_lfm2_entities()`・`call_masker/call_reviewer` の LFM2 パス
- LFM2 部分文字列競合（長さ降順ソート）・複数出現の全置換

**パイプライン** (`test_pipeline.py`)
- 空文字列・1文字・空白のみの早期リターン
- `enabled_layers` による Layer 選択（Layer 1 のみ／Layer 2 のみ）
- Layer 3 失敗時の Layer 1+2 フォールバック（confidence=0.7）
- Layer 4 失敗時の Layer 3 フォールバック（confidence=0.8）
- `excluded_tags` が全レイヤーに伝播することの確認
- `layer_counts` の正確性・`replacements` の `layer` フィールド付与
- NER 例外時のグレースフルフォールバック

**ファイルハンドラー** (`test_file_handlers.py`)
- XLSX: PII セルのマスク・数値セル／短文字列セルのスキップ・`_masked` サフィックス・元ファイル非上書き・`replacements_log` の `location` フィールド
- PPTX: テキストフレームのマスク・スライド番号の `location` 記録・短文テキストのスキップ
- DOCX: 段落マスク・テーブルセルマスク・`氏名`/`ふりがな` ラベル隣接セルの未マスク警告

**Streamlit UI** (`test_ui.py`)
- `check_lm_studio_connection()`: 正常接続・`ConnectionError`・`Timeout`・空モデルリスト・URL の `/models` 変換
- `_build_replacement_log_text()`: 空リスト・単一エントリ・複数ファイルグループ化・合計件数・レイヤーラベル
- `AppTest`: LM Studio 状態表示・フォルダ未入力時のボタン無効化・無効パス時のエラー表示

---

## 新しいファイル形式の追加方法

1. `file_handlers/` に `{format}_handler.py` を作成
2. `base.py` の `FileHandler` プロトコルを実装
3. `main.py` のハンドラーディスパッチに登録
4. `config.py` の `SUPPORTED_EXTENSIONS` に拡張子を追加
5. `.gitignore` / `.dockerignore` にマスク済み出力パターンを追加

---

## 新しい PII カテゴリの追加方法

### Layer 1（正規表現）

`core/layer1_regex.py` に正規表現パターンと対応タグを追加する。

### Layer 2（NER）

GiNZA のエンティティラベルと対応タグのマッピングを `core/layer2_ner.py` に追加する。

### Layer 3 / 4（LLM）

システムプロンプトの検出対象リストに追加する。

---

## コードスタイル

- Python 3.11 以上の型ヒントを使用
- データクラス（`@dataclass`）でモデルを定義
- ファイルハンドラーは `Protocol` ベースで実装
- 設定値は `config.py` に集約し、ハードコードしない
