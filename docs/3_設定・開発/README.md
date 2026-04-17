# 3_設定・開発

環境設定・デプロイ手順・開発ガイドを収録したフォルダです。
概要設計書（`0_概要設計/pii_masker_design.md`）の「7. ビルド・配布」「8. セキュリティ・運用」「11. 引き継ぎ事項」に対応します。

## ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| [configuration.md](configuration.md) | `config.py` の設定項目・環境変数・Docker デプロイ手順・MCP 接続設定・ネットワークセキュリティ |
| [development.md](development.md) | ローカル開発環境セットアップ・依存関係・テスト実行・新機能追加ガイド |

## このフォルダを読む目的

- **Docker で起動する手順**を知りたい → `configuration.md`
- **環境変数で変更できる設定値**を確認したい → `configuration.md`
- **Claude Desktop への MCP 接続方法**を調べたい → `configuration.md`
- **ローカルで開発を始める手順**を知りたい → `development.md`
- **テストを追加・実行する方法**を確認したい → `development.md`
- **新しいファイル形式や PII カテゴリを追加する手順**を調べたい → `development.md`
