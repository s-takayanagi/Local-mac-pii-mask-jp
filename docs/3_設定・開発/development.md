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
# ローカル
pytest tests/ -v

# Docker コンテナ内
docker run --rm pii-masker python -m pytest tests/ -v

# カバレッジ付き
pytest tests/ -v --cov=core --cov-report=term-missing
```

### テスト構成

| ファイル | 対象 |
|---------|------|
| `tests/test_layer1_regex.py` | Layer 1 正規表現パターン |

### Layer 1 テストケース

- 携帯電話番号（`090-XXXX-XXXX`、全角ハイフン含む）
- 固定電話番号（市外局番あり）
- メールアドレス
- 郵便番号（`XXX-XXXX`）
- URL（`https://...`）
- 複合パターン（複数 PII が混在するテキスト）

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
