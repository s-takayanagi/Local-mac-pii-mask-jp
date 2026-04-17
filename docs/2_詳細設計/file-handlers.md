# ファイルハンドラー設計

## 基本方針

1. 元ファイルは**コピーしてから処理**する（元ファイルを上書きしない）
2. 出力ファイル名: `{元ファイル名}_masked.{拡張子}`
3. ファイルの構造・フォーマット・スタイルは保持する
4. 各セル / 段落 / テキストフレームに対して `mask_text()` を適用する

---

## 基底プロトコル（`file_handlers/base.py`）

```python
class FileHandler(Protocol):
    def process(self, input_path: Path, output_path: Path) -> ProcessResult:
        ...
```

すべてのハンドラーは `ProcessResult` を返す。

```python
@dataclass
class ProcessResult:
    output_path: Path
    total_replacements: int
    errors: list[str]
```

---

## Excel ハンドラー（`file_handlers/xlsx_handler.py`）

**処理フロー**

```
.xlsx コピー
    │
    ▼
全シートをループ
    │
    ▼
各セルの値を取得（文字列のみ）
    │
    ▼
mask_text() 適用
    │
    ▼
セルに書き戻し
    │
    ▼
保存（openpyxl）
```

**保持されるもの**
- セルの書式（フォント・背景色・罫線）
- シート構造・行列幅
- 数式セルはスキップ（文字列のみ処理）

---

## PowerPoint ハンドラー（`file_handlers/pptx_handler.py`）

**処理フロー**

```
.pptx コピー
    │
    ▼
全スライドをループ
    │
    ▼
図形を再帰的に探索（グループ図形対応）
    │
    ├── テキストフレーム → 各段落の runs を処理
    └── テーブル → 各セルのテキストを処理
    │
    ▼
mask_text() 適用
    │
    ▼
保存（python-pptx）
```

**保持されるもの**
- スライドレイアウト・マスター
- 図形のアニメーション・位置・サイズ
- フォント・段落スタイル

---

## Word ハンドラー（`file_handlers/docx_handler.py`）

**処理フロー**

```
.docx コピー
    │
    ▼
本文段落をループ
    ├── 段落内の全 runs を結合して mask_text() 適用
    └── 最初の run に書き戻し、残りの runs をクリア
    │
    ▼
テーブルセルをループ（各セルも同様に処理）
    │
    ▼
保存（python-docx）
```

**runs 結合の理由**

Word は 1 つの段落を複数の run（書式単位）に分割して保存する場合がある。
テキストを run 単位で個別処理すると PII が途中で分断されて検出できないため、
段落テキストを一度結合してから処理する。

**保持されるもの**
- 最初の run の書式（フォント・太字・色）
- 段落スタイル（見出し・本文など）
- テーブル構造

**制約**
- 2 番目以降の run の独自書式は失われる可能性がある
