import shutil
from pathlib import Path
from docx import Document
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult

_LABEL_TO_TAG: dict[str, str] = {
    "氏名": "[氏名]",
    "ふりがな": "[氏名]",
}


def _merge_numeric(totals: dict, values: dict) -> None:
    for k, v in values.items():
        totals[k] = totals.get(k, 0) + v


def _mask_paragraph(
    para, model: str, url: str, enabled_layers: set[str] | None = None, excluded_tags: set[str] | None = None
) -> tuple[int, dict, dict, list[str], list[dict]]:
    if not para.runs or not para.text.strip():
        return 0, {}, {}, [], []
    result = mask_text(para.text, model, url, enabled_layers, excluded_tags)
    errs = [result.error] if result.error else []
    if result.final_text == para.text:
        return 0, result.layer_counts, result.layer_elapsed, errs, []
    para.runs[0].text = result.final_text
    for run in para.runs[1:]:
        run.text = ""
    return len(result.replacements), result.layer_counts, result.layer_elapsed, errs, result.replacements


def process_docx(path: Path, model: str, lm_studio_url: str, enabled_layers: set[str] | None = None, excluded_tags: set[str] | None = None) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    doc = Document(output)
    total = 0
    errors: list[str] = []
    warnings: list[str] = []
    layer_totals: dict = {}
    layer_elapsed: dict = {}
    replacements_log: list[dict] = []

    for para_idx, para in enumerate(doc.paragraphs):
        try:
            count, lc, le, errs, reps = _mask_paragraph(para, model, lm_studio_url, enabled_layers, excluded_tags)
            total += count
            _merge_numeric(layer_totals, lc)
            _merge_numeric(layer_elapsed, le)
            errors.extend(errs)
            for r in reps:
                replacements_log.append({**r, "location": f"段落{para_idx + 1}"})
        except Exception as e:
            errors.append(f"paragraph: {e}")

    def _process_table(table, loc_prefix: str) -> int:
        subtotal = 0
        for row_idx, row in enumerate(table.rows):
            cells = row.cells
            label_tag: str | None = None
            label_text: str = ""
            if cells:
                label_text = cells[0].text.strip()
                label_tag = _LABEL_TO_TAG.get(label_text)

            for col_idx, cell in enumerate(cells):
                loc = f"{loc_prefix}/行{row_idx + 1}/列{col_idx + 1}"
                cell_replaced = 0

                for para in cell.paragraphs:
                    try:
                        count, lc, le, errs, reps = _mask_paragraph(para, model, lm_studio_url, enabled_layers, excluded_tags)
                        subtotal += count
                        cell_replaced += count
                        _merge_numeric(layer_totals, lc)
                        _merge_numeric(layer_elapsed, le)
                        errors.extend(errs)
                        for r in reps:
                            replacements_log.append({**r, "location": loc})
                    except Exception as e:
                        errors.append(f"table cell: {e}")

                # 氏名/ふりがなラベルの隣の値セルが未マスクなら警告
                if (
                    col_idx == 1
                    and label_tag is not None
                    and cell_replaced == 0
                    and cell.text.strip()
                ):
                    warnings.append(
                        f"{loc} の「{cell.text.strip()[:30]}」は{label_text}の可能性があります。マスキングされていないことを確認してください。"
                    )

                for nested_table in cell.tables:
                    subtotal += _process_table(nested_table, f"{loc}(nested)")
        return subtotal

    for tbl_idx, table in enumerate(doc.tables):
        total += _process_table(table, f"表{tbl_idx + 1}")

    doc.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
        layer_elapsed=layer_elapsed,
        replacements_log=replacements_log,
        warnings=warnings,
    )
