# データモデル設計

## モデル定義場所

`models.py`

---

## コアデータモデル

### `MaskResult`

パイプライン全体の最終出力。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `final_text` | `str` | マスク済みテキスト |
| `replacements` | `list[dict]` | 置換記録のリスト。各 dict に `"original"`, `"tag"`, `"layer"` キーを含む |
| `confidence` | `float` | マスキング完全性スコア（0.0〜1.0） |
| `error` | `str \| None` | エラーメッセージ（正常時は None） |
| `layer_counts` | `dict` | レイヤー別検出件数 `{"layer1": N, "layer2": N, "layer3": N, "layer4": N}` |

---

### `MaskerResult`

Layer 3 LLM マスキングの出力。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `masked_text` | `str` | マスク済みテキスト |
| `replacements` | `list[Replacement]` | 置換記録のリスト |

---

### `ReviewerResult`

Layer 4 LLM レビューの出力。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `final_text` | `str` | レビュー後のテキスト |
| `additional` | `list[Replacement]` | 追加で検出した置換記録 |
| `confidence` | `float` | 信頼スコア（0.0〜1.0） |

---

### `ProcessResult`

ファイル処理の結果。

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `output_path` | `Path` | 出力ファイルのパス |
| `total_replacements` | `int` | 総置換件数 |
| `errors` | `list[str]` | エラーメッセージのリスト |
| `layer_totals` | `dict` | ファイル全体のレイヤー別合計件数 `{"layer1": N, ...}` |
| `replacements_log` | `list[dict]` | 置換ログ。各 dict に `"location"`, `"original"`, `"tag"`, `"layer"` キーを含む |
| `warnings` | `list[str]` | 未マスクの可能性がある箇所の警告（docx のみ生成） |

---

### 置換記録（dict）

実装上は `@dataclass` ではなく `dict` で管理。

| キー | 型 | 説明 |
|-----|-----|------|
| `original` | `str` | 元のテキスト（マスク前） |
| `tag` | `str` | 置換に使用したタグ（例: `[氏名]`） |
| `layer` | `str` | 検出したレイヤー（`"layer1"` 〜 `"layer4"`）。`MaskResult.replacements` に付与 |
| `location` | `str` | ファイル内の位置（例: `"Sheet1!A1"`、`"スライド2/テキストボックス1"`）。`ProcessResult.replacements_log` に付与 |

---

## LLM API の入出力スキーマ

### Layer 3 出力（JSON）

```json
{
  "masked_text": "マスク済みテキスト",
  "replacements": [
    { "original": "山田太郎", "tag": "[氏名]" },
    { "original": "example@email.com", "tag": "[メール]" }
  ]
}
```

### Layer 4 出力（JSON）

```json
{
  "final_text": "最終マスク済みテキスト",
  "additional": [
    { "original": "太郎", "tag": "[氏名]" }
  ],
  "confidence": 0.95
}
```

---

## マスキングタグ定数

`config.py` または各 layer ファイル内で定義される文字列定数。

```python
TAG_NAME      = "[氏名]"
TAG_ADDRESS   = "[住所]"
TAG_PHONE     = "[電話番号]"
TAG_EMAIL     = "[メール]"
TAG_ORG       = "[会社名]"
TAG_POSTAL    = "[郵便番号]"
TAG_ID        = "[識別番号]"
TAG_URL       = "[URL]"
TAG_OTHER     = "[個人情報]"
```
