# PII Masker - プロジェクト概要

## 目的

日本語ビジネス文書（Excel / PowerPoint / Word）に含まれる個人情報（PII）を、完全ローカル環境でマスキングするツール。

**設計原則**

- **クラウド非通信**: 処理中に PII が外部へ送信されない
- **オフライン動作**: LM Studio のローカルモデルのみ使用
- **完全コンテナ化**: Python・GiNZA・NER モデルをすべて Docker 内に封入

---

## 対応ファイル形式

| 形式 | 拡張子 | ライブラリ |
|------|--------|-----------|
| Excel | `.xlsx` | openpyxl |
| PowerPoint | `.pptx` | python-pptx |
| Word | `.docx` | python-docx |

---

## マスキング対象タグ一覧

| タグ | 対象情報 |
|------|----------|
| `[氏名]` | 人名（フル・略称含む） |
| `[住所]` | 住所・住所断片 |
| `[電話番号]` | 携帯・固定電話番号 |
| `[メール]` | メールアドレス |
| `[会社名]` | 企業・組織名 |
| `[郵便番号]` | 郵便番号 |
| `[識別番号]` | マイナンバーなど 12 桁の ID |
| `[URL]` | URL |
| `[個人情報]` | 上記以外の個人情報 |

---

## LFM2-350M-PII-Extract-JP 専用モード

LM Studio で LFM2-350M-PII-Extract-JP モデルを選択すると、専用モードで動作します。

| 項目 | 汎用 LLM モード | LFM2 専用モード |
|------|--------------|----------------|
| システムプロンプト | MASKER_SYSTEM / REVIEWER_SYSTEM | `Extract <address>, <company_name>, ...` |
| 出力形式 | `{"masked_text": ..., "replacements": [...]}` | `{"human_name": [...], "address": [...], ...}` |
| temperature | 0.05 | 0（greedy decoding） |
| ライセンス | 各モデルに依存 | LFM Open License v1.0（$10M以上の企業は要確認） |

---

## システム全体像

```
ホストマシン
├── Docker Desktop
│   └── pii-masker コンテナ
│       ├── Python 3.11
│       ├── GiNZA / ja_ginza_electra（NER モデル内蔵）
│       ├── Streamlit UI（ポート 8501）
│       └── MCP サーバー（stdio）
└── LM Studio（別アプリ、ポート 1234）
    └── 任意モデル（推奨: Gemma-4 E4B / その他動作確認済み: Qwen3 1.7B / LFM2-350M-PII-Extract-JP）
```

---

## メモリ使用量の目安（M1 16GB Mac）

| コンポーネント | 消費メモリ |
|--------------|-----------|
| OS + アプリ | ~4 GB |
| LM Studio | ~0.5 GB |
| LLM モデル（推奨: Gemma-4 E4B） | ~0.4〜4 GB |
| GiNZA ja_ginza_electra | ~1.5 GB |
| pii-masker コンテナ | ~0.5 GB |
| **合計** | **~7〜10 GB** |
