import shutil
from pathlib import Path
import openpyxl
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def process_xlsx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    wb = openpyxl.load_workbook(output)
    total = 0
    errors: list[str] = []

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or len(cell.value.strip()) <= 1:
                    continue
                try:
                    result = mask_text(cell.value, model, lm_studio_url)
                    cell.value = result.final_text
                    total += len(result.replacements)
                except Exception as e:
                    errors.append(f"{ws.title}!{cell.coordinate}: {e}")

    wb.save(output)
    return ProcessResult(output_path=output, total_replacements=total, errors=errors)
