import shutil
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_numeric(totals: dict, values: dict) -> None:
    for k, v in values.items():
        totals[k] = totals.get(k, 0) + v


def _iter_shapes(shapes):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes(shape.shapes)
        else:
            yield shape


def _mask_text_frame(
    tf, model: str, url: str, enabled_layers: set[str] | None = None, excluded_tags: set[str] | None = None
) -> tuple[int, dict, dict, list[str], list[dict]]:
    total = 0
    layer_totals: dict = {}
    layer_elapsed: dict = {}
    errors: list[str] = []
    reps: list[dict] = []
    for para in tf.paragraphs:
        for run in para.runs:
            if not run.text or len(run.text.strip()) <= 1:
                continue
            result = mask_text(run.text, model, url, enabled_layers, excluded_tags)
            run.text = result.final_text
            total += len(result.replacements)
            _merge_numeric(layer_totals, result.layer_counts)
            _merge_numeric(layer_elapsed, result.layer_elapsed)
            if result.error:
                errors.append(result.error)
            reps.extend(result.replacements)
    return total, layer_totals, layer_elapsed, errors, reps


def process_pptx(path: Path, model: str, lm_studio_url: str, enabled_layers: set[str] | None = None, excluded_tags: set[str] | None = None) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    prs = Presentation(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}
    layer_elapsed: dict = {}
    replacements_log: list[dict] = []

    for slide_idx, slide in enumerate(prs.slides):
        for shape in _iter_shapes(slide.shapes):
            try:
                if shape.has_text_frame:
                    count, lc, le, errs, reps = _mask_text_frame(shape.text_frame, model, lm_studio_url, enabled_layers, excluded_tags)
                    total += count
                    _merge_numeric(layer_totals, lc)
                    _merge_numeric(layer_elapsed, le)
                    errors.extend(errs)
                    loc = f"スライド{slide_idx + 1}/{shape.name}"
                    for r in reps:
                        replacements_log.append({**r, "location": loc})
                if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                    tbl = shape.table
                    for r in range(len(tbl.rows)):
                        for c in range(len(tbl.columns)):
                            count, lc, le, errs, reps = _mask_text_frame(
                                tbl.cell(r, c).text_frame, model, lm_studio_url, enabled_layers, excluded_tags
                            )
                            total += count
                            _merge_numeric(layer_totals, lc)
                            _merge_numeric(layer_elapsed, le)
                            errors.extend(errs)
                            loc = f"スライド{slide_idx + 1}/{shape.name}/行{r + 1}/列{c + 1}"
                            for rep in reps:
                                replacements_log.append({**rep, "location": loc})
            except Exception as e:
                errors.append(f"Slide{slide_idx + 1}/{shape.name}: {e}")

    prs.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
        layer_elapsed=layer_elapsed,
        replacements_log=replacements_log,
    )
