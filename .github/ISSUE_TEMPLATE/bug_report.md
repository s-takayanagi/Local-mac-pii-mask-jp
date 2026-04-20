---
name: 🐛 バグ報告
about: 動作不良・予期しない挙動の報告
title: "[Bug] "
labels: bug
assignees: ''
---

## 概要

（何が起きたか、1〜2 文で）

## 再現手順

1.
2.
3.

## 期待する挙動

（どうなるはずだったか）

## 実際の挙動

（実際に何が起きたか。エラーメッセージ・スタックトレースがあれば貼付）

```
（ログをここに）
```

## 環境

- OS: （例: macOS 14.5 / Apple Silicon / 16GB RAM）
- Docker Desktop バージョン:
- LM Studio バージョン:
- 使用した LLM モデル: （例: `google/gemma-4-e4b`）
- PII Masker のバージョン / コミットハッシュ:
- 入力ファイル形式: （xlsx / pptx / docx）

## 処理設定

- [ ] Layer 1（正規表現）
- [ ] Layer 2（GiNZA NER）
- [ ] Layer 3（LLM Masker）
- [ ] Layer 4（LLM Reviewer）
- 除外した PII 種別:
- 処理モード: （GUI / CLI / MCP）

## 追加情報

（スクリーンショット・サンプルデータなど。**PII を含む実データは貼らないでください**）

---

### 確認事項

- [ ] 既存の Issue に同様の報告がないことを確認しました
- [ ] 個人情報・機密情報を含むデータを本 Issue に貼付していません
- [ ] 脆弱性に関する報告の場合は [SECURITY.md](../../SECURITY.md) に従います
