# 1_アーキテクチャ設計

システム全体の構成・コンポーネント関係・データモデルを収録したフォルダです。
概要設計書（`0_概要設計/pii_masker_design.md`）の「4. システム設計」「5. コンポーネント構成」をもとに詳述しています。

## ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| [architecture.md](architecture.md) | ディレクトリ構成・実行モード・コンポーネント間の通信・Docker 構成 |
| [data-models.md](data-models.md) | データクラス定義・LLM の入出力 JSON スキーマ・マスキングタグ定数 |

## このフォルダを読む目的

- **フォルダ構成とファイルの役割**を把握したい → `architecture.md`
- **Docker/docker-compose の設定内容**を確認したい → `architecture.md`
- **`MaskResult` などのデータクラス**の定義を調べたい → `data-models.md`
- **LLM が返す JSON の形式**を確認したい → `data-models.md`
