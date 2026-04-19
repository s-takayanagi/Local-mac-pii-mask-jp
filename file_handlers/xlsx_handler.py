import shutil
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import openpyxl
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_numeric(totals: dict, values: dict) -> None:
    for k, v in values.items():
        totals[k] = totals.get(k, 0) + v


def _mask_many(
    texts: list[str],
    model: str,
    url: str,
    enabled_layers: set[str] | None,
    excluded_tags: set[str] | None,
    max_workers: int,
):
    if max_workers > 1 and len(texts) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            return list(ex.map(
                lambda t: mask_text(t, model, url, enabled_layers, excluded_tags),
                texts,
            ))
    return [mask_text(t, model, url, enabled_layers, excluded_tags) for t in texts]


def process_xlsx(
    path: Path,
    model: str,
    lm_studio_url: str,
    enabled_layers: set[str] | None = None,
    excluded_tags: set[str] | None = None,
    max_workers: int = 1,
) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    wb = openpyxl.load_workbook(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}
    layer_elapsed: dict = {}
    replacements_log: list[dict] = []

    # Phase 1: collect cells to mask
    tasks: list[tuple[str, object, str]] = []  # (ws_title, cell_ref, text)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if not isinstance(cell.value, str) or len(cell.value.strip()) <= 1:
                    continue
                tasks.append((ws.title, cell, cell.value))

    if not tasks:
        wb.save(output)
        return ProcessResult(
            output_path=output,
            total_replacements=0,
            errors=errors,
            layer_totals=layer_totals,
            layer_elapsed=layer_elapsed,
            replacements_log=replacements_log,
        )

    # Phase 2: mask (serial or parallel)
    texts = [t[2] for t in tasks]
    results = _mask_many(texts, model, lm_studio_url, enabled_layers, excluded_tags, max_workers)

    # Phase 3: write back & aggregate
    for (ws_title, cell, _orig), result in zip(tasks, results):
        try:
            cell.value = result.final_text
            total += len(result.replacements)
            _merge_numeric(layer_totals, result.layer_counts)
            _merge_numeric(layer_elapsed, result.layer_elapsed)
            if result.error:
                errors.append(f"{ws_title}!{cell.coordinate}: {result.error}")
            loc = f"{ws_title}!{cell.coordinate}"
            for r in result.replacements:
                replacements_log.append({**r, "location": loc})
        except Exception as e:
            errors.append(f"{ws_title}!{cell.coordinate}: {e}")

    wb.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
        layer_elapsed=layer_elapsed,
        replacements_log=replacements_log,
    )
