# 2_詳細設計

各コンポーネントの処理フロー・実装仕様を収録したフォルダです。
概要設計書（`0_概要設計/pii_masker_design.md`）の「6. 実装詳細」に対応します。

## ドキュメント一覧

| ファイル | 内容 |
|---------|------|
| [pipeline.md](pipeline.md) | 4 層マスキングパイプラインの各レイヤーの処理内容・正規表現パターン・LLM プロンプト方針 |
| [file-handlers.md](file-handlers.md) | xlsx / pptx / docx ハンドラーの処理フロー・実装上の注意点 |
| [interfaces.md](interfaces.md) | Streamlit UI・MCP サーバーツール・CLI・LM Studio API の仕様 |

## このフォルダを読む目的

- **各 Layer が何を検出するか**を確認したい → `pipeline.md`
- **LLM へのシステムプロンプトの内容**を確認したい → `pipeline.md`
- **Excel/Word/PowerPoint の処理で注意すべき点**を知りたい → `file-handlers.md`
- **MCP ツールの引数と戻り値**を調べたい → `interfaces.md`
- **Streamlit UI の画面構成**を把握したい → `interfaces.md`
