import shutil
from pathlib import Path
from docx import Document
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_layer_counts(totals: dict, counts: dict) -> None:
    for k, v in counts.items():
        totals[k] = totals.get(k, 0) + v


def _mask_paragraph(para, model: str, url: str) -> tuple[int, dict, list[str], list[dict]]:
    if not para.runs or not para.text.strip():
        return 0, {}, [], []
    result = mask_text(para.text, model, url)
    errs = [result.error] if result.error else []
    if result.final_text == para.text:
        return 0, result.layer_counts, errs, []
    para.runs[0].text = result.final_text
    for run in para.runs[1:]:
        run.text = ""
    return len(result.replacements), result.layer_counts, errs, result.replacements


def process_docx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    doc = Document(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}
    replacements_log: list[dict] = []

    for para_idx, para in enumerate(doc.paragraphs):
        try:
            count, lc, errs, reps = _mask_paragraph(para, model, lm_studio_url)
            total += count
            _merge_layer_counts(layer_totals, lc)
            errors.extend(errs)
            for r in reps:
                replacements_log.append({**r, "location": f"段落{para_idx + 1}"})
        except Exception as e:
            errors.append(f"paragraph: {e}")

    for tbl_idx, table in enumerate(doc.tables):
        for row_idx, row in enumerate(table.rows):
            for col_idx, cell in enumerate(row.cells):
                for para in cell.paragraphs:
                    try:
                        count, lc, errs, reps = _mask_paragraph(para, model, lm_studio_url)
                        total += count
                        _merge_layer_counts(layer_totals, lc)
                        errors.extend(errs)
                        loc = f"表{tbl_idx + 1}/行{row_idx + 1}/列{col_idx + 1}"
                        for r in reps:
                            replacements_log.append({**r, "location": loc})
                    except Exception as e:
                        errors.append(f"table cell: {e}")

    doc.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
        replacements_log=replacements_log,
    )
