import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="PII Masker")
    parser.add_argument(
        "--mode",
        choices=["ui", "mcp", "cli"],
        default="ui",
        help="起動モード: ui=StreamlitGUI, mcp=MCPサーバー, cli=コマンドライン",
    )
    parser.add_argument("--folder", help="CLIモード時の処理フォルダパス")
    args = parser.parse_args()

    if args.mode == "ui":
        import subprocess
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", "ui/streamlit_app.py"],
            check=True,
        )
    elif args.mode == "mcp":
        from mcp.server import mcp
        mcp.run(transport="stdio")
    elif args.mode == "cli":
        if not args.folder:
            parser.error("--folder を指定してください")
        from core.pipeline import mask_text
        from config import DEFAULT_MODEL, LM_STUDIO_URL, SUPPORTED_EXTENSIONS
        from pathlib import Path

        folder = Path(args.folder)
        if not folder.is_dir():
            print(f"エラー: フォルダが見つかりません: {args.folder}")
            sys.exit(1)

        files = [
            f for f in folder.iterdir()
            if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~")
        ]
        if not files:
            print("対象ファイルが見つかりませんでした")
            sys.exit(0)

        from file_handlers.xlsx_handler import process_xlsx
        from file_handlers.pptx_handler import process_pptx
        from file_handlers.docx_handler import process_docx

        handlers = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}
        total = 0
        for f in files:
            try:
                result = handlers[f.suffix.lower()](f, DEFAULT_MODEL, LM_STUDIO_URL)
                print(f"✓ {f.name} → {result.output_path.name} ({result.total_replacements}件)")
                total += result.total_replacements
            except Exception as e:
                print(f"✗ {f.name}: {e}")
        print(f"\n合計 {total} 件置換")


if __name__ == "__main__":
    main()
