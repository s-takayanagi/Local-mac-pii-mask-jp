# Contributing to PII Masker

PII Masker へのコントリビュートに興味をお持ちいただき、ありがとうございます。本プロジェクトは技術プレビュー版であり、フィードバック・バグ報告・改善提案を歓迎します。

---

## はじめに

- 行動規範: 本プロジェクトへの参加にあたっては [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) への同意をお願いします。
- ライセンス: 本プロジェクトは技術プレビュー版であり、正式ライセンスは検討中です（[LICENSE](LICENSE) 参照）。プルリクエストを提出いただいた場合、将来的に決定される正式ライセンス（MIT / Apache-2.0 等を想定）の下で貢献コードを配布することに同意したものとみなします。ライセンス条件にご懸念がある場合は、事前に Issue でご相談ください。

---

## コントリビュートの種類

- 🐛 **バグ報告**: GitHub Issues で [バグ報告テンプレート](.github/ISSUE_TEMPLATE/bug_report.md) をご利用ください。
- 💡 **機能要望**: [機能要望テンプレート](.github/ISSUE_TEMPLATE/feature_request.md) をご利用ください。
- 🔒 **脆弱性報告**: 公開 Issue ではなく [SECURITY.md](SECURITY.md) の手順に従ってください。
- 📝 **ドキュメント改善**: typo・翻訳・説明の明確化、すべて歓迎です。
- 🧪 **テスト追加**: カバレッジ向上や回帰テストの追加は特に歓迎します。
- 🔧 **コード修正・機能追加**: 大きな変更の場合は事前に Issue で相談いただけると助かります。

---

## 開発環境のセットアップ

```bash
git clone https://github.com/s-takayanagi/Pii-masker-.git
cd Pii-masker-

# Docker イメージをビルド
bash build/build_docker.sh

# テスト実行
docker run --rm -v "$(pwd)":/app -w /app --entrypoint "" pii-masker \
  sh -c "pip install pytest pytest-cov && python -m pytest tests/ -v"
```

Python や依存ライブラリはすべて Docker 内に封じ込まれています。ホスト側での `pip install` は不要です。

---

## ブランチ運用

- `main`: 常にビルド・テストが通る状態を維持します。
- 機能追加・修正は `feature/xxx` または `fix/xxx` のトピックブランチで作業し、`main` に PR を出してください。
- PR は `main` にマージ後、トピックブランチは削除します。

---

## コミット・PR のガイドライン

### コミットメッセージ

以下のプレフィクスを推奨します（Conventional Commits 準拠）。

| プレフィクス | 用途 |
|---|---|
| `feat:` | 新機能 |
| `fix:` | バグ修正 |
| `docs:` | ドキュメントのみ |
| `test:` | テストの追加・修正 |
| `refactor:` | 挙動を変えないリファクタ |
| `perf:` | パフォーマンス改善 |
| `build:` | ビルド・Docker 関連 |
| `ci:` | CI 設定 |
| `chore:` | その他雑務 |

例:

```
feat: Layer3 で LLM タイムアウト時のリトライを追加
fix: xlsx ハンドラーで結合セルがスキップされる問題を修正
```

### プルリクエスト

- PR テンプレート（[.github/PULL_REQUEST_TEMPLATE.md](.github/PULL_REQUEST_TEMPLATE.md)）に従って記入してください。
- PR のタイトルはコミットメッセージと同じ形式（`feat: ...`）を推奨します。
- レビュー前に、ご自身で以下を確認してください:
  - [ ] テストが追加・更新されている
  - [ ] 既存のテストがすべて通る
  - [ ] ドキュメント（README・docs/）が必要に応じて更新されている
  - [ ] 機密情報（API キー、個人情報、社内データ）が含まれていない

---

## コーディング規約

- **Python**: PEP 8 準拠。型ヒントは可能な限り付与してください。
- **日本語コメント**: 日本語中心のプロジェクトのため、コメント・docstring は日本語・英語どちらでも歓迎します。
- **テスト**: 新機能には対応するユニットテストを追加してください。LLM・NER・ネットワーク依存の箇所はモックを使ってください（`tests/` の既存パターンを参照）。
- **依存追加**: 新規ライブラリの追加は `pyproject.toml` に明記し、PR 説明で追加理由を述べてください。ライセンスが明確でない依存（GPL 系など）の追加は避けてください。

---

## 質問・相談

- 仕様・設計レベルの相談は GitHub Issues の `discussion` ラベルをご利用ください（または Discussions タブが有効な場合はそちら）。
- 返信はベストエフォートです。技術プレビュー版のため、SLA はありません。

ご協力ありがとうございます！
