import shutil
from pathlib import Path
from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _merge_layer_counts(totals: dict, counts: dict) -> None:
    for k, v in counts.items():
        totals[k] = totals.get(k, 0) + v


def _iter_shapes(shapes):
    for shape in shapes:
        if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
            yield from _iter_shapes(shape.shapes)
        else:
            yield shape


def _mask_text_frame(tf, model: str, url: str) -> tuple[int, dict, list[str]]:
    total = 0
    layer_totals: dict = {}
    errors: list[str] = []
    for para in tf.paragraphs:
        for run in para.runs:
            if not run.text or len(run.text.strip()) <= 1:
                continue
            result = mask_text(run.text, model, url)
            run.text = result.final_text
            total += len(result.replacements)
            _merge_layer_counts(layer_totals, result.layer_counts)
            if result.error:
                errors.append(result.error)
    return total, layer_totals, errors


def process_pptx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    prs = Presentation(output)
    total = 0
    errors: list[str] = []
    layer_totals: dict = {}

    for slide_idx, slide in enumerate(prs.slides):
        for shape in _iter_shapes(slide.shapes):
            try:
                if shape.has_text_frame:
                    count, lc, errs = _mask_text_frame(shape.text_frame, model, lm_studio_url)
                    total += count
                    _merge_layer_counts(layer_totals, lc)
                    errors.extend(errs)
                if shape.shape_type == MSO_SHAPE_TYPE.TABLE:
                    tbl = shape.table
                    for r in range(len(tbl.rows)):
                        for c in range(len(tbl.columns)):
                            count, lc, errs = _mask_text_frame(
                                tbl.cell(r, c).text_frame, model, lm_studio_url
                            )
                            total += count
                            _merge_layer_counts(layer_totals, lc)
                            errors.extend(errs)
            except Exception as e:
                errors.append(f"Slide{slide_idx + 1}/{shape.name}: {e}")

    prs.save(output)
    return ProcessResult(
        output_path=output,
        total_replacements=total,
        errors=errors,
        layer_totals=layer_totals,
    )
