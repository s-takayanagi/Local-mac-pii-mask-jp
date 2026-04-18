import shutil
from pathlib import Path
from docx import Document
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_layer_counts(totals: dict, counts: dict) -> None:
    for k, v in counts.items():
        totals[k] = totals.get(k, 0) + v


def _mask_paragraph(para, model: str, url: str) -> tuple[int, dict, list[str]]:
    if not para.runs or not para.text.strip():
        return 0, {}, []
    result = mask_text(para.text, model, url)
    errs = [result.error] if result.error else []
    if result.final_text == para.text:
        return 0, result.layer_counts, errs
    para.runs[0].text = result.final_text
    for run in para.runs[1:]:
        run.text = ""
    return len(result.replacements), result.layer_counts, errs


def process_docx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    doc = Document(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}

    for para in doc.paragraphs:
        try:
            count, lc, errs = _mask_paragraph(para, model, lm_studio_url)
            total += count
            _merge_layer_counts(layer_totals, lc)
            errors.extend(errs)
        except Exception as e:
            errors.append(f"paragraph: {e}")

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    try:
                        count, lc, errs = _mask_paragraph(para, model, lm_studio_url)
                        total += count
                        _merge_layer_counts(layer_totals, lc)
                        errors.extend(errs)
                    except Exception as e:
                        errors.append(f"table cell: {e}")

    doc.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
    )
