# PII Masker — 概要設計書

**対象読者**: Claude Code での実装担当者  
**作成日**: 2026-04-18  
**ステータス**: 設計確定・実装待ち

---

## 1. 背景と目的

### 1.1 課題

多くの企業では、社内ルールとして**ClaudeなどのクラウドLLMにPII（個人情報）を
入力することが禁止**されている。しかし現実の業務では顧客データを含む
Excel（.xlsx）・PowerPoint（.pptx）・Word（.docx）ファイルを頻繁に扱うため、
LLMを活用したい場面でも使えないという摩擦が生じている。

LLMのトークン上限問題も重なり、PIIを含む文書をそのまま投入することへの
心理的・規則的ハードルが高い。

### 1.2 解決策の方針

「**PIIをローカルで除去してからClaudeに渡す**」という2ステップワークフローを
確立する。ローカル処理は LM Studio 上で動かす小型LLMが担い、マスキング済み
テキストだけを Claude（Cowork・Code・chat）に渡す。

```
[社内文書（PII含む）]
        ↓
  PII Masker（本アプリ）
  完全ローカル・オフライン
        ↓
[マスキング済み文書]
        ↓
  Claude（Cowork / Code / chat）
  安全に利用可能
```

---

## 2. 要件定義

### 2.1 機能要件

| # | 要件 | 優先度 |
|---|------|--------|
| F1 | フォルダを指定して配下の対象ファイルを一括マスキング | 必須 |
| F2 | 対応形式：.xlsx / .pptx / .docx | 必須 |
| F3 | 書式・レイアウトを維持して同名_maskedファイルを出力 | 必須 |
| F4 | 処理進捗・置換件数をリアルタイム表示 | 必須 |
| F5 | LM Studio接続状態の確認・モデル選択 | 必須 |
| F6 | Claude Desktop から MCP ツールとして呼び出し可能 | 重要 |
| F7 | macOS デスクトップアプリ（.app）として配布 | 重要 |
| F8 | マルチエージェント（Masker→Reviewer）による精度向上 | 重要 |

### 2.2 非機能要件

| # | 要件 |
|---|------|
| N1 | 完全オフライン動作（LM Studio APIへの通信のみ、外部通信なし） |
| N2 | Python環境なしで動作（PyInstaller .app化） |
| N3 | M1 MacBook Pro 16GB RAM での安定動作 |
| N4 | 使用ライブラリ・モデルの商用利用ライセンス適合 |
| N5 | 可逆マスキング不要（シンプルな不可逆置換） |

---

## 3. ライセンス調査結果（2026-04-18 時点）

### 3.1 LFM2-350M-PII-Extract-JP の評価と除外理由

当初 Layer3（LLMマスキング層）の第一候補として検討していたが、
**ライセンス上の懸念により採用を見送る。**

調査結果：
- ライセンス名：**LFM Open License v1.0**（Apache 2.0 ベースだが独自条項あり）
- 年間売上 **$10M（約15億円）未満** の企業は商用利用無償
- 年間売上 $10M 以上の企業は `sales@liquid.ai` に連絡して商用ライセンスの取得が必要
- 利用企業の売上規模によっては $10M 超の可能性があり、オープンソースプロジェクトとして
  あらゆる規模の企業が安心して使える構成にする必要がある

判断：ライセンス確定まで待つよりも **Apache 2.0 の Qwen2.5-7B で代替実装**し、
将来的に LFM2 採用に切り替えられる設計にする。

> **将来対応**: LFM2-350M-PII-Extract-JP は 229MB という極小サイズで、
> 5カテゴリ（address, company_name, email_address, human_name, phone_number）の
> 抽出に特化した優れたモデルである。法務確認後に差し替えることで精度向上が見込める。

### 3.2 採用コンポーネントのライセンス確認済み一覧

| コンポーネント | ライセンス | 商用利用 | 備考 |
|---|---|---|---|
| **Qwen2.5-7B-Instruct** (Masker/Reviewer) | Apache 2.0 | ✅ 無制限 | 主力モデル |
| **GiNZA v5 + ja_ginza_electra** | **MIT** | ✅ 無制限 | NINJAL×Megagon Labs 共同研究、MIT確認済み |
| **spaCy** | MIT | ✅ 無制限 | GiNZA の基盤 |
| **LM Studio** (実行環境) | 独自（法人無償化済み） | ✅ 2025/7〜法人無償 | $10M超でもアプリ自体は無償 |
| **openpyxl** | MIT | ✅ | xlsx処理 |
| **python-pptx** | MIT | ✅ | pptx処理 |
| **python-docx** | MIT | ✅ | docx処理 |
| **Streamlit** | Apache 2.0 | ✅ | UI フレームワーク |
| **streamlit-desktop-app** | MIT | ✅ | PyInstaller .app化ラッパー |
| **FastMCP** | Apache 2.0 | ✅ | MCP Server 実装 |
| **requests** | Apache 2.0 | ✅ | LM Studio API呼び出し |

**注意**: Codestral（Mistral Non-Production License）は明示的に業務利用禁止。
DeepSeek R1/V3 は MIT だが情報管理観点で別途評価が必要。本プロジェクトでは使用しない。

### 3.3 GiNZA ライセンス詳細

`ja_ginza_electra` は NINJAL（国立国語研究所）と Megagon Labs の共同研究契約の下、
**MIT License で配布が許可**されている。PyPI、Hugging Face の両ページで MIT 明記を確認。
mC4 由来のデータは ODC Attribution License（帰属表示のみ）であり商用利用を妨げない。

---

## 4. システム設計

### 4.1 全体アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                    PII Masker                               │
│                                                             │
│  ┌──────────────────┐    ┌─────────────────────────────┐  │
│  │  顔① .app (GUI)  │    │  顔② MCP Server (stdio)     │  │
│  │  Streamlit UI    │    │  FastMCP                    │  │
│  │                  │    │  tools:                     │  │
│  │  フォルダ選択     │    │  - mask_folder(path)        │  │
│  │  進捗表示        │    │  - mask_file(path)          │  │
│  │  完了サマリー    │    │  - mask_text(text)          │  │
│  └────────┬─────────┘    └──────────────┬──────────────┘  │
│           │                              │                  │
│           └──────────┬───────────────────┘                 │
│                      │                                      │
│           ┌──────────▼────────────┐                        │
│           │   Pipeline Engine     │                        │
│           │                       │                        │
│           │  ┌─────────────────┐  │                        │
│           │  │ Layer1: Regex   │  │  電話・メール・郵便番号  │
│           │  └────────┬────────┘  │  マイナンバー等         │
│           │           │           │                        │
│           │  ┌────────▼────────┐  │                        │
│           │  │ Layer2: GiNZA  │  │  氏名・住所（NER）      │
│           │  │ ja_ginza_electra│  │                        │
│           │  └────────┬────────┘  │                        │
│           │           │           │                        │
│           │  ┌────────▼────────┐  │                        │
│           │  │ Layer3: LLM    │  │  自由記述中の残存PII    │
│           │  │ Qwen2.5-7B     │  │  (Maskerエージェント)  │
│           │  └────────┬────────┘  │                        │
│           │           │           │                        │
│           │  ┌────────▼────────┐  │                        │
│           │  │ Reviewer: LLM  │  │  見落とし検出           │
│           │  │ Qwen2.5-7B     │  │  (Reviewerエージェント) │
│           │  └────────┬────────┘  │                        │
│           └──────────┬────────────┘                        │
│                      │                                      │
│           ┌──────────▼────────────┐                        │
│           │ File Handlers         │                        │
│           │ xlsx / pptx / docx    │                        │
│           └───────────────────────┘                        │
└──────────────────────────────────────────────────────────────┘
              ↕ localhost:1234 (OpenAI互換API)
┌─────────────────────────────────────────────────────────────┐
│  LM Studio                                                  │
│  モデル: Qwen2.5-7B-Instruct (Q4_K_M, ~5GB)               │
│  ※ 1モデルのみ起動。Masker/Reviewerはシリアル処理           │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 M1 16GB でのメモリ設計

```
OS + 業務アプリ（Chrome/Slack/VSCode）  : ~4GB
LM Studio 本体                          : ~0.5GB
Qwen2.5-7B Q4_K_M                       : ~5GB
GiNZA ja_ginza_electra モデル           : ~1.5GB
PII Masker アプリ本体                   : ~0.5GB
────────────────────────────────────────────────
合計                                    : ~11.5GB
余裕                                    : ~4.5GB ← 安全圏
```

**重要**: M1 16GBでは2モデル同時起動（LFM2+Qwen）は不可。1モデルで
Masker・Reviewer 両方をシリアル処理するため、処理時間が長くなるが安全。

### 4.3 マルチエージェント設計（シリアル処理）

```
テキスト入力
    ↓
[前処理: Regex]       100ms以内・確実なパターン一掃
    ↓
[Masker Agent]        Qwen2.5-7B、temperature=0.05
  プロンプト: 氏名・住所・会社名を[タグ]に置換
  出力: {"masked_text": "...", "replacements": [...]}
    ↓
[Reviewer Agent]      同モデル・別システムプロンプト
  プロンプト: 見落としを検出して追加マスク
  出力: {"final_text": "...", "additional": [...], "confidence": 0.0}
    ↓
final_text を元ファイルへ書き戻し
```

### 4.4 マスキング対象と置換タグ

#### Layer1（正規表現）で処理するもの

| パターン | 置換タグ | 正規表現 |
|---------|---------|---------|
| 固定電話 | `[電話番号]` | `0\d{1,4}[-−]\d{2,4}[-−]\d{3,4}` |
| 携帯電話 | `[電話番号]` | `0[789]0[-−]\d{4}[-−]\d{4}` |
| メールアドレス | `[メール]` | `[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}` |
| 郵便番号 | `[郵便番号]` | `\d{3}[-−]\d{4}` |
| 日付（生年月日形式） | `[生年月日]` | `\d{4}年\s*\d{1,2}月\s*\d{1,2}日` |
| 12桁数字（マイナンバー等） | `[識別番号]` | `(?<!\d)\d{12}(?!\d)` |
| URL | `[URL]` | `https?://\S+` |

#### Layer2（GiNZA NER）で処理するもの

GiNZA が検出する固有表現タイプのうち、PII に該当するもの：

| GiNZA ラベル | 置換タグ |
|---|---|
| `Person` / `PERSON` | `[氏名]` |
| `City` / `Province` / `Address` | `[住所]` |
| `Organization` / `Company` | `[会社名]` |
| `Phone` | `[電話番号]`（Layer1漏れの補完） |
| `Email` | `[メール]`（Layer1漏れの補完） |

一般的な地名（東京都・大阪市など行政単位）は除外ロジックを入れる。

#### Layer3（Qwen2.5-7B）で処理するもの

上記2層で検出できなかった文脈依存のPII。具体的には：
- 「〜さん」「〜様」「〜部長」等の敬称付き人名
- 住所の一部（丁目・番地・号室のみ記載）
- 社員番号・顧客IDのような非定型識別情報
- 「私の担当は田中です」のような埋め込み人名

### 4.5 ファイルハンドラー設計

#### xlsx（openpyxl）

```
workbook → worksheets → rows → cells
各セルの cell.value（str型のみ）にパイプライン適用
書式・数式・結合セルは保持
```

注意点：
- セル値が None や数値の場合はスキップ
- 1文字以下の文字列もスキップ（処理コスト削減）
- `~$` で始まるロックファイルは除外

#### pptx（python-pptx）

```
presentation → slides → shapes → text_frame → paragraphs → runs
各 run.text にパイプライン適用
フォント・サイズ・色は run レベルで保持される
```

注意点：
- `shape.has_text_frame` が False のシェイプはスキップ
- テーブルセルは `shape.table.cell(r, c).text_frame` で別途処理
- グループシェイプは再帰処理が必要

#### docx（python-docx）

```
document → paragraphs → runs
段落全体をまとめて処理してから先頭 run に書き戻す
（run 分割による書式崩れを防ぐため）
```

注意点：
- `paragraph.text` で一旦全文取得してパイプライン適用
- 書き戻し時は `runs[0].text = final_text; runs[1:].text = ""` とする
- テーブル内の段落も `table.cell(r, c).paragraphs` で処理

---

## 5. コンポーネント構成

```
pii_masker/
│
├── README.md
├── requirements.txt              # pip依存一覧
├── pyproject.toml                # uv / Poetry 設定
│
├── main.py                       # エントリポイント
│                                 # --mode ui: Streamlit起動
│                                 # --mode mcp: MCPサーバー起動
│                                 # --mode cli: CLIモード
│
├── core/
│   ├── __init__.py
│   ├── pipeline.py               # 3層パイプライン統合
│   │   └── mask_text(text, model, lm_studio_url) -> MaskResult
│   │
│   ├── layer1_regex.py           # 正規表現マスキング
│   │   └── apply_regex(text) -> (masked_text, replacements)
│   │
│   ├── layer2_ner.py             # GiNZA NER マスキング
│   │   └── apply_ner(text) -> (masked_text, replacements)
│   │   # 初回実行時に ja_ginza_electra を遅延ロード
│   │
│   └── layer3_llm.py             # LM Studio API 呼び出し
│       ├── call_masker(text, model, url) -> MaskerResult
│       └── call_reviewer(masked_text, model, url) -> ReviewerResult
│
├── file_handlers/
│   ├── __init__.py
│   ├── base.py                   # 共通インターフェース
│   │   └── ProcessResult(output_path, total_replacements, errors)
│   ├── xlsx_handler.py           # openpyxl
│   ├── pptx_handler.py           # python-pptx（テーブル・グループ対応）
│   └── docx_handler.py           # python-docx（テーブル対応）
│
├── ui/
│   └── streamlit_app.py          # Streamlit UI
│       # 画面1: 設定（フォルダ選択、モデル選択、LM Studio接続確認）
│       # 画面2: 処理中（ファイル別進捗、リアルタイムログ）
│       # 画面3: 完了（サマリー、出力フォルダ表示）
│
├── mcp/
│   └── server.py                 # FastMCP stdio server
│       # tool: mask_text(text: str) -> str
│       # tool: mask_file(file_path: str) -> str  (output_path)
│       # tool: mask_folder(folder_path: str) -> str (summary)
│
├── config.py                     # 設定管理
│   # LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"
│   # DEFAULT_MODEL = "qwen2.5-7b-instruct"
│   # OUTPUT_SUFFIX = "_masked"
│   # SUPPORTED_EXTENSIONS = [".xlsx", ".pptx", ".docx"]
│
├── models.py                     # Pydantic モデル定義
│   # MaskResult, MaskerResult, ReviewerResult, ProcessResult
│
└── build/
    ├── build_app.sh              # PyInstaller .app ビルドスクリプト
    ├── build_mcpb.sh             # .mcpb パッケージビルドスクリプト
    ├── PII_Masker.spec           # PyInstaller spec ファイル
    └── manifest.json            # MCPB マニフェスト（Claude Desktop 連携用）
```

---

## 6. 実装詳細

### 6.1 LM Studio API 呼び出し

LM Studio は OpenAI 互換 API を `http://localhost:1234/v1` で提供する。
`chat/completions` エンドポイントを使い、JSON レスポンスを強制する。

```python
# layer3_llm.py の骨格

MASKER_SYSTEM = """\
あなたは日本語文書の個人情報マスキング専門AIです。
以下の情報を検出し対応するタグに置換してください。

置換対象:
- 人名（姓名・フルネーム・名前単体） → [氏名]
- 住所（都道府県〜番地・号室）       → [住所]
- 会社名・組織名（固有名詞）         → [会社名]
- 社員番号・顧客番号                 → [識別番号]
- その他個人を特定できる固有情報     → [個人情報]

ルール:
- すでに[タグ]形式の箇所は変更しない
- 一般的な地名・公的機関名（東京都・国税庁等）は対象外
- テキストの意味・構造を壊さない

必ず以下のJSONのみ出力（前置き・説明不要）:
{"masked_text": "...", "replacements": [{"original": "...", "tag": "..."}]}
"""

REVIEWER_SYSTEM = """\
あなたは個人情報マスキングの品質レビュアーAIです。
マスク済みテキストを受け取り、見落とされた個人情報を追加マスクします。

確認ポイント:
- 残存している人名（日本語・英語）
- 住所の断片（丁目・番地・マンション名）
- 会社名・ブランド名

ルール:
- すでに[タグ]形式の箇所はそのまま保持
- 過検出（一般名詞・地名等）は避ける
- 変更がない場合も final_text に入力テキストをそのまま返す

必ず以下のJSONのみ出力:
{"final_text": "...", "additional": [{"original": "...", "tag": "..."}], "confidence": 0.0}
"""

def call_lm_studio(system: str, user: str, url: str, model: str) -> dict:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
    }
    resp = requests.post(url, json=payload, timeout=120)
    resp.raise_for_status()
    raw = resp.json()["choices"][0]["message"]["content"]
    # JSONフェンス除去
    clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
    start, end = clean.find("{"), clean.rfind("}") + 1
    return json.loads(clean[start:end])
```

### 6.2 パイプライン統合

```python
# pipeline.py の骨格

@dataclass
class MaskResult:
    final_text: str
    replacements: list[dict]
    confidence: float
    error: str | None = None

def mask_text(text: str, model: str, lm_studio_url: str) -> MaskResult:
    if not text or not text.strip() or len(text.strip()) <= 1:
        return MaskResult(final_text=text, replacements=[], confidence=1.0)

    # Layer1: 正規表現
    l1_text, l1_reps = apply_regex(text)

    # Layer2: GiNZA NER
    l2_text, l2_reps = apply_ner(l1_text)

    # Layer3: LLM Masker
    masker_result = call_masker(l2_text, model, lm_studio_url)
    if masker_result is None:
        return MaskResult(final_text=l2_text, replacements=l1_reps+l2_reps,
                         confidence=0.7, error="Masker failed")

    masked = masker_result.get("masked_text", l2_text)

    # Layer4: LLM Reviewer
    reviewer_result = call_reviewer(masked, model, lm_studio_url)
    if reviewer_result is None:
        final = masked
        confidence = 0.8
        additional = []
    else:
        final = reviewer_result.get("final_text", masked)
        confidence = reviewer_result.get("confidence", 0.9)
        additional = reviewer_result.get("additional", [])

    all_reps = l1_reps + l2_reps + masker_result.get("replacements", []) + additional
    return MaskResult(final_text=final, replacements=all_reps, confidence=confidence)
```

### 6.3 Streamlit UI 構成

```python
# streamlit_app.py の主要構造

def main():
    st.set_page_config(page_title="PII Masker", layout="wide")

    # サイドバー: 設定
    with st.sidebar:
        # LM Studio 接続確認（ページ読み込み時に自動チェック）
        lm_status = check_lm_studio_connection()
        st.badge("LM Studio: " + ("接続中" if lm_status["ok"] else "未接続"))

        # モデル選択
        models = lm_status.get("models", [DEFAULT_MODEL])
        selected_model = st.selectbox("モデル", models)

        # 出力サフィックス設定
        suffix = st.text_input("出力サフィックス", value="_masked")

    # メインエリア: 3ステップ
    # Step1: フォルダ選択
    folder = st.text_input("処理フォルダを入力してください")
    # ※ Streamlit の file_uploader はフォルダ選択不可なのでテキスト入力
    # .app の場合は st.button でOS標準のフォルダ選択ダイアログを開くことも検討

    # Step2: 実行
    if st.button("マスキング開始", disabled=not folder or not lm_status["ok"]):
        run_masking(folder, selected_model, suffix)

    # Step3: 完了サマリー（session_state で管理）
```

**フォルダ選択の実装方針**:
Streamlit ではネイティブのフォルダ選択ダイアログが使えないため、
以下のいずれかを採用する：
1. テキスト入力（エンジニア向けに十分）
2. `tkinter.filedialog.askdirectory()` を subprocess で呼ぶラッパー
   （.app 化時に tkinter が含まれるかの確認要）

### 6.4 MCP Server（Claude Desktop 連携）

```python
# mcp/server.py

from fastmcp import FastMCP
from core.pipeline import mask_text
from file_handlers.xlsx_handler import process_xlsx
from file_handlers.pptx_handler import process_pptx
from file_handlers.docx_handler import process_docx
from config import DEFAULT_MODEL, LM_STUDIO_URL, SUPPORTED_EXTENSIONS
from pathlib import Path

mcp = FastMCP("PII Masker")

@mcp.tool()
def mask_text_tool(text: str) -> str:
    """テキスト内の個人情報をマスキングします。
    氏名、住所、電話番号、メールアドレス、会社名等を[タグ]に置換します。
    """
    result = mask_text(text, DEFAULT_MODEL, LM_STUDIO_URL)
    return result.final_text

@mcp.tool()
def mask_file(file_path: str) -> str:
    """指定ファイル（xlsx/pptx/docx）の個人情報をマスキングします。
    マスキング済みファイルのパスと置換件数を返します。
    """
    path = Path(file_path)
    if not path.exists():
        return f"エラー: ファイルが見つかりません: {file_path}"
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return f"エラー: 非対応形式です（対応: xlsx, pptx, docx）"

    handlers = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}
    result = handlers[path.suffix.lower()](path, DEFAULT_MODEL, LM_STUDIO_URL)
    return f"完了: {result.output_path}（{result.total_replacements}件置換）"

@mcp.tool()
def mask_folder(folder_path: str) -> str:
    """フォルダ内の全対応ファイルを一括マスキングします。
    処理結果のサマリーを返します。
    """
    folder = Path(folder_path)
    if not folder.is_dir():
        return f"エラー: フォルダが見つかりません: {folder_path}"

    files = [f for f in folder.iterdir()
             if f.suffix.lower() in SUPPORTED_EXTENSIONS
             and not f.name.startswith("~")]

    if not files:
        return "対象ファイルが見つかりませんでした"

    results = []
    total_reps = 0
    errors = []

    for f in files:
        handlers = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}
        try:
            r = handlers[f.suffix.lower()](f, DEFAULT_MODEL, LM_STUDIO_URL)
            total_reps += r.total_replacements
            results.append(f"✓ {f.name} → {r.output_path.name} ({r.total_replacements}件)")
        except Exception as e:
            errors.append(f"✗ {f.name}: {e}")

    summary = f"処理完了: {len(files)}件 / {total_reps}件置換\n"
    summary += "\n".join(results)
    if errors:
        summary += "\n\nエラー:\n" + "\n".join(errors)
    return summary

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### 6.5 Claude Desktop への接続方法

#### 方法A: JSON設定ファイル直接編集（エンジニア向け）

`~/Library/Application Support/Claude/claude_desktop_config.json` を編集：

```json
{
  "mcpServers": {
    "pii-masker": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/pii_masker",
        "run",
        "main.py",
        "--mode",
        "mcp"
      ]
    }
  }
}
```

Claude Desktop を完全再起動すると、チャット入力欄の「+」ボタンから
`pii-masker` ツールが利用可能になる。

#### 方法B: .mcpb Desktop Extension パッケージ（非エンジニア向け）

`.mcpb`（ZIP形式）に以下を同梱：

```
pii_masker.mcpb (ZIP)
├── manifest.json     ← MCPB メタデータ
├── server/
│   └── server        ← PyInstaller でビルドした単一バイナリ（MCP modeのみ）
└── icon.png
```

`manifest.json` の例：

```json
{
  "name": "PII Masker",
  "version": "1.0.0",
  "description": "日本語文書の個人情報をローカルでマスキングします。LM Studioが必要です。",
  "author": "your-name-or-org",
  "server": {
    "type": "binary",
    "platforms": {
      "macos-arm64": "server/server"
    }
  },
  "tools": [
    {"name": "mask_text", "description": "テキストのPIIをマスキング"},
    {"name": "mask_file", "description": "ファイルのPIIをマスキング"},
    {"name": "mask_folder", "description": "フォルダ一括マスキング"}
  ],
  "user_config": {
    "lm_studio_url": {
      "type": "string",
      "label": "LM Studio URL",
      "default": "http://localhost:1234/v1/chat/completions",
      "description": "LM Studioのローカルサーバーアドレス"
    },
    "model_name": {
      "type": "string",
      "label": "モデル名",
      "default": "qwen2.5-7b-instruct",
      "description": "LM Studioで起動中のモデル名"
    }
  }
}
```

**注意**: .mcpb の Python バンドルには制約あり（pydantic 等コンパイル済み依存を
ポータブルにバンドルできない）。実用上は Node.js ラッパー経由か、
PyInstaller で単一バイナリ化して binary タイプで配布する方が安定する。

---

## 7. ビルド・配布

### 7.1 Streamlit .app のビルド

`streamlit-desktop-app`（MIT License）を使用する。これは Streamlit +
PyInstaller + pywebview の組み合わせで、ブラウザを起動せずネイティブ
ウィンドウで動作させる。

```bash
# 環境準備
pip install streamlit streamlit-desktop-app pyinstaller

# .app ビルド（macOS arm64）
streamlit-desktop-app build ui/streamlit_app.py \
  --name "PII Masker" \
  --icon build/icon.icns \
  --streamlit-options --theme.base=dark

# 出力: dist/PII Masker.app
```

**PyInstaller での GiNZA の扱い**:
`ja_ginza_electra` は初回実行時にモデルファイルをダウンロードするため、
`.app` に事前組み込みすることが難しい。以下2案：

1. **初回起動時ダウンロード**：初回のみネット接続を許可してモデルをキャッシュ
   （`~/.cache/pii_masker/ginza/` に保存）
2. **バンドルに含める**：`--add-data` で spaCy モデルディレクトリを指定
   （.app サイズが 500MB 程度になるが配布後は完全オフライン）

**推奨**: 初回ダウンロード方式（Option 1）。配布時は初回のみ接続を
許可する旨を README に明記する。

### 7.2 依存関係管理

```toml
# pyproject.toml
[project]
name = "pii-masker"
version = "1.0.0"
requires-python = ">=3.11,<3.13"  # PyInstaller の制約に合わせる
dependencies = [
    "streamlit>=1.35",
    "streamlit-desktop-app>=0.3",
    "fastmcp>=2.10",
    "openpyxl>=3.1",
    "python-pptx>=0.6",
    "python-docx>=1.1",
    "requests>=2.31",
    "ginza>=5.2",
    "ja-ginza-electra>=5.2",
    "spacy>=3.7",
]
```

---

## 8. セキュリティ・運用

### 8.1 通信範囲

| 通信先 | タイミング | 目的 |
|--------|-----------|------|
| `localhost:1234` | マスキング処理時 | LM Studio API（テキスト推論） |
| Hugging Face / PyPI | 初回起動時のみ | GiNZA モデルダウンロード（Option 1選択時） |
| LM Studio ダウンロードサーバー | モデル初回DL時 | Qwen2.5-7B モデルファイル取得 |
| **外部（処理中）** | **なし** | **PIIは一切外部に出ない** |

### 8.2 出力ファイル管理

- 出力ファイルは元ファイルと同フォルダに `_masked` サフィックスで保存
- 元ファイルは上書きしない（安全のため）
- ログ・置換リストはアプリメモリのみ（ファイル書き出ししない）

### 8.3 LM Studio ポート

LM Studio のデフォルトは `localhost:1234`。インターネットには公開しない。
Firewall で 1234 番ポートへの外部アクセスをブロックしておくことを推奨。

---

## 9. 実装優先順位とフェーズ

### Phase 1（コア機能、Week 1〜2）

1. `config.py` と `models.py`（データクラス定義）
2. `core/layer1_regex.py`（正規表現）
3. `core/layer2_ner.py`（GiNZA、遅延ロード）
4. `core/layer3_llm.py`（LM Studio API呼び出し）
5. `core/pipeline.py`（統合）
6. `file_handlers/xlsx_handler.py`
7. `file_handlers/pptx_handler.py`（テーブル・グループ対応）
8. `file_handlers/docx_handler.py`（テーブル対応）
9. 単体テスト（`tests/`）

### Phase 2（UI + .app化、Week 3）

10. `ui/streamlit_app.py`
11. PyInstaller ビルドスクリプト
12. `.app` 動作確認（M1 MacBook）

### Phase 3（Claude Desktop連携、Week 4）

13. `mcp/server.py`（FastMCP）
14. `claude_desktop_config.json` 設定確認
15. `.mcpb` パッケージビルド（余裕があれば）

### Phase 4（中期、Month 2）

16. LFM2-350M-PII-Extract-JP への差し替え（ライセンス確認後）
17. 組織展開に向けた配布パッケージ整備
18. 処理速度ベンチマーク（M1 16GB での実測）

---

## 10. 既知の制約と対策

| 制約 | 内容 | 対策 |
|------|------|------|
| GiNZA の人名検出精度 | 「山田が来た」の「山田」は高精度だが「田中さんへ」のような敬称込みは Layer3 LLM で補完 | Layer3 の Masker プロンプトで敬称パターンを明示 |
| Qwen2.5-7B の処理速度 | M1 で 18〜25 tok/s（200字テキストで約5秒/呼び出し） | セル単位ではなく段落・行単位でまとめて送信してAPI呼び出し回数を削減 |
| pptx のグループシェイプ | `shape.shape_type == MSO_SHAPE_TYPE.GROUP` は再帰が必要 | `iterate_shapes()` ヘルパー関数で再帰処理 |
| docx の run 書き戻し | run を分割すると書式が崩れる | 先頭 run に全文を書き、残りの run は空文字に |
| .app サイズ | GiNZA + Streamlit + PyInstaller で 300〜600MB | 初回ダウンロード方式で .app 本体を軽量化 |
| LM Studio の起動要件 | マスキング処理前にユーザーが LM Studio を起動する必要あり | アプリ起動時に接続チェック → 未接続なら案内メッセージ表示 |

---

## 11. Claude Code への引き継ぎ事項

### 最初にやること

```bash
# リポジトリ初期化
mkdir pii_masker && cd pii_masker
uv init
uv add streamlit streamlit-desktop-app fastmcp openpyxl python-pptx python-docx requests ginza ja-ginza-electra spacy

# LM Studio が起動していることを確認（localhost:1234）
# Qwen2.5-7B-Instruct を LM Studio でダウンロード・起動

# 開発実行
uv run streamlit run ui/streamlit_app.py         # UI確認
uv run python main.py --mode mcp                 # MCP確認
```

### テスト用サンプルファイル

以下の内容でテスト用 xlsx を作成して動作確認：

```
山田太郎,yamada.taro@example.com,090-1234-5678,東京都渋谷区1-2-3
田中花子,090-9876-5432,〒150-0001,株式会社テスト
```

期待出力：
```
[氏名],[メール],[電話番号],[住所]
[氏名],[電話番号],[郵便番号],[会社名]
```

### LM Studio 設定メモ

- モデル：`Qwen2.5-7B-Instruct`（Q4_K_M 推奨、約5GB）
- LM Studio の「Local Server」タブでサーバーを起動
- デフォルトポート：1234
- モデル名はLM Studioの表示名と一致させる（APIで `/v1/models` を叩いて確認可）

### 将来の LFM2 差し替え手順

`core/layer3_llm.py` の `MASKER_SYSTEM` と `call_masker()` を以下に変更：

```python
# LFM2-350M-PII-Extract-JP 用システムプロンプト（ChatMLテンプレート）
LFM2_SYSTEM = "Extract <address>, <company_name>, <email_address>, <human_name>, <phone_number>"

def call_masker_lfm2(text: str, url: str) -> dict:
    """LFM2-350M-PII-Extract-JP 向け呼び出し（構造化JSON出力）"""
    # temperature=0.0 で確定的出力
    # json-schema モードで出力を強制
    ...
```

---

*以上が PII Masker の概要設計書です。Claude Code での実装に際して不明点があれば
設計判断の根拠を上記から参照してください。*
