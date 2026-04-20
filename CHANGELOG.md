# Changelog

本ファイルは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) の形式に従います。
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準拠する予定ですが、技術プレビュー期間中は破壊的変更がパッチ/マイナー更新に含まれる場合があります。

## [Unreleased]

### Added
- `THIRD_PARTY_NOTICES.md` を追加し、依存ライブラリ・LLM モデルのライセンスを明記
- `LICENSE`（暫定・ライセンス検討中）を追加
- `SECURITY.md` で脆弱性報告手順を整備
- `DISCLAIMER.md` で技術プレビュー版としての免責事項を明文化
- `CONTRIBUTING.md` / `CODE_OF_CONDUCT.md` を追加
- GitHub Actions による CI（pytest）と Dependabot を追加
- GitHub Issue / PR テンプレートを追加

### Changed
- README に技術プレビュー版としての注意書きセクションを追加
- MCP サーバーセクションに「未検証」の注記を追加
- README のライセンス欄を `MIT` → `検討中（TBD）` に変更

---

## [1.0.0] - 2026-04

初版リリース（技術プレビュー）。

### Added
- 4 層パイプラインによる日本語 PII マスキング機能
  - Layer 1: 正規表現（電話番号・メール・郵便番号・URL・マイナンバー・住所）
  - Layer 2: GiNZA NER（氏名・住所・会社名）
  - Layer 3: LLM Masker（文脈依存の残存 PII）
  - Layer 4: LLM Reviewer（見落とし検出・過検出修正）
- `.xlsx` / `.pptx` / `.docx` ファイルハンドラー
- Streamlit ベースの GUI
- CLI モード
- MCP サーバー（Claude Desktop 連携・未検証）
- macOS 向け `install.command` / `start.command` / `stop.command`
- `.dmg` ビルドスクリプト（`build/make_dmg.sh`）
- ログレベルの UI からの変更機能
- 122 個のユニットテスト

---

[Unreleased]: https://github.com/s-takayanagi/Pii-masker-/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/s-takayanagi/Pii-masker-/releases/tag/v1.0.0
