# Third-Party Notices

本プロジェクト（PII Masker）は以下の第三者ソフトウェア・モデルを利用しています。各コンポーネントには、それぞれのライセンスが適用されます。本ファイルは主要な依存関係を網羅することを目的としていますが、間接依存（transitive dependencies）まで完全には列挙していません。網羅的な一覧は以下のコマンドで自動生成できます。

```bash
# Docker コンテナ内で依存ライブラリのライセンス一覧を生成
docker run --rm --entrypoint "" pii-masker \
  sh -c "pip install pip-licenses && pip-licenses --format=markdown --with-urls"
```

---

## Python ライブラリ（直接依存）

| ライブラリ | バージョン | ライセンス | 用途 | URL |
|---|---|---|---|---|
| streamlit | >=1.35 | Apache-2.0 | Web UI | https://streamlit.io/ |
| streamlit-desktop-app | >=0.3 | Apache-2.0 | デスクトップアプリ化 | https://pypi.org/project/streamlit-desktop-app/ |
| fastmcp | >=2.10 | Apache-2.0 | MCP サーバー実装 | https://github.com/jlowin/fastmcp |
| openpyxl | >=3.1 | MIT | .xlsx 読み書き | https://openpyxl.readthedocs.io/ |
| python-pptx | >=0.6 | MIT | .pptx 読み書き | https://python-pptx.readthedocs.io/ |
| python-docx | >=1.1 | MIT | .docx 読み書き | https://python-docx.readthedocs.io/ |
| requests | >=2.31 | Apache-2.0 | HTTP クライアント | https://requests.readthedocs.io/ |
| GiNZA | >=5.2 | MIT | 日本語 NLP | https://megagonlabs.github.io/ginza/ |
| ja-ginza-electra | >=5.2 | MIT | 日本語 NER モデル | https://github.com/megagonlabs/ginza |
| spaCy | >=3.7 | MIT | NLP フレームワーク | https://spacy.io/ |

### 開発用依存（optional）

| ライブラリ | バージョン | ライセンス | 用途 |
|---|---|---|---|
| pytest | >=8.0 | MIT | テストフレームワーク |
| pytest-cov | >=5.0 | MIT | カバレッジ計測 |

---

## LLM モデル（ユーザーが LM Studio 経由で取得）

以下のモデルは本リポジトリには含まれません。LM Studio 経由で各自ダウンロードいただく形を想定しています。**利用にあたっては、それぞれの配布元が定める利用規約・ライセンスを必ず確認してください。**

| モデル | ライセンス | 注意事項 | 配布元 |
|---|---|---|---|
| Gemma-4 E4B（推奨） | [Gemma Terms of Use](https://ai.google.dev/gemma/terms) | Google の定める利用規約に同意が必要。禁止用途（Prohibited Use Policy）あり。 | Google |
| Qwen3 1.7B | Apache-2.0 | 商用利用可。 | Alibaba Cloud |
| LFM2-350M-PII-Extract-JP | [LFM Open License v1.0](https://www.liquid.ai/lfm-open-license) | 前年度売上 US$10M 以上の組織は商用利用にあたり別途ライセンス契約が必要。 | Liquid AI |

---

## Docker ベースイメージ

| コンポーネント | ライセンス | 備考 |
|---|---|---|
| `python:3.11-slim`（Debian ベース） | PSF License（Python）、各種 OSS（Debian 部分） | 公式イメージ |

---

## ライセンス全文の取得方法

各 Python パッケージのライセンス全文は、インストール後に以下で取得できます。

```bash
docker run --rm --entrypoint "" pii-masker \
  sh -c "pip install pip-licenses && pip-licenses --with-license-file --format=json --no-license-path" \
  > third_party_licenses.json
```

モデルのライセンス全文は、上記「配布元」の各 URL を参照してください。

---

## 注意事項

- 本ファイルは best-effort で作成しており、内容の正確性・完全性を保証するものではありません。商用利用・再配布を検討される場合は、必ず各依存コンポーネントの公式ライセンス文書をご自身で確認してください。
- 間接依存（transitive dependencies）についても、配布形態によっては表示義務が発生する場合があります。本プロジェクトの再配布を行う際は、上記 `pip-licenses` コマンドで全依存のライセンス一覧を生成することを推奨します。
- 記載に誤り・漏れを発見された場合は、GitHub Issues でご報告ください。
