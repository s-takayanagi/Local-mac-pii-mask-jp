import shutil
from pathlib import Path
import openpyxl
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_layer_counts(totals: dict, counts: dict) -> None:
    for k, v in counts.items():
        totals[k] = totals.get(k, 0) + v


def process_xlsx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    wb = openpyxl.load_workbook(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}

    replacements_log: list[dict] = []

    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or len(cell.value.strip()) <= 1:
                    continue
                try:
                    result = mask_text(cell.value, model, lm_studio_url)
                    cell.value = result.final_text
                    total += len(result.replacements)
                    _merge_layer_counts(layer_totals, result.layer_counts)
                    if result.error:
                        errors.append(f"{ws.title}!{cell.coordinate}: {result.error}")
                    loc = f"{ws.title}!{cell.coordinate}"
                    for r in result.replacements:
                        replacements_log.append({**r, "location": loc})
                except Exception as e:
                    errors.append(f"{ws.title}!{cell.coordinate}: {e}")

    wb.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
        replacements_log=replacements_log,
    )
