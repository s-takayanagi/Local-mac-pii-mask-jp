from pathlib import Path
from fastmcp import FastMCP
from core.pipeline import mask_text
from file_handlers.xlsx_handler import process_xlsx
from file_handlers.pptx_handler import process_pptx
from file_handlers.docx_handler import process_docx
from config import DEFAULT_MODEL, LM_STUDIO_URL, SUPPORTED_EXTENSIONS

mcp = FastMCP("PII Masker")

_HANDLERS = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}


@mcp.tool()
def mask_text_tool(text: str) -> str:
    """テキスト内の個人情報をマスキングします。氏名、住所、電話番号、メールアドレス、会社名等を[タグ]に置換します。"""
    result = mask_text(text, DEFAULT_MODEL, LM_STUDIO_URL)
    return result.final_text


@mcp.tool()
def mask_file(file_path: str) -> str:
    """指定ファイル（xlsx/pptx/docx）の個人情報をマスキングします。マスキング済みファイルのパスと置換件数を返します。"""
    path = Path(file_path)
    if not path.exists():
        return f"エラー: ファイルが見つかりません: {file_path}"
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        return "エラー: 非対応形式です（対応: xlsx, pptx, docx）"
    result = _HANDLERS[path.suffix.lower()](path, DEFAULT_MODEL, LM_STUDIO_URL)
    return f"完了: {result.output_path}（{result.total_replacements}件置換）"


@mcp.tool()
def mask_folder(folder_path: str) -> str:
    """フォルダ内の全対応ファイルを一括マスキングします。処理結果のサマリーを返します。"""
    folder = Path(folder_path)
    if not folder.is_dir():
        return f"エラー: フォルダが見つかりません: {folder_path}"

    files = [
        f for f in folder.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~")
    ]
    if not files:
        return "対象ファイルが見つかりませんでした"

    lines = []
    total = 0
    errors = []
    for f in files:
        try:
            r = _HANDLERS[f.suffix.lower()](f, DEFAULT_MODEL, LM_STUDIO_URL)
            total += r.total_replacements
            lines.append(f"✓ {f.name} → {r.output_path.name} ({r.total_replacements}件)")
        except Exception as e:
            errors.append(f"✗ {f.name}: {e}")

    summary = f"処理完了: {len(files)}件 / {total}件置換\n" + "\n".join(lines)
    if errors:
        summary += "\n\nエラー:\n" + "\n".join(errors)
    return summary


if __name__ == "__main__":
    mcp.run(transport="stdio")
