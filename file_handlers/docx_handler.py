import shutil
from pathlib import Path
from docx import Document
from core.pipeline import mask_text
from file_handlers.base import masked_output_path
from models import ProcessResult


def _mask_paragraph(para, model: str, url: str) -> int:
    if not para.runs or not para.text.strip():
        return 0
    result = mask_text(para.text, model, url)
    if result.final_text == para.text:
        return 0
    para.runs[0].text = result.final_text
    for run in para.runs[1:]:
        run.text = ""
    return len(result.replacements)


def process_docx(path: Path, model: str, lm_studio_url: str) -> ProcessResult:
    output = masked_output_path(path)
    shutil.copy2(path, output)

    doc = Document(output)
    total = 0
    errors: list[str] = []

    for para in doc.paragraphs:
        try:
            total += _mask_paragraph(para, model, lm_studio_url)
        except Exception as e:
            errors.append(f"paragraph: {e}")

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    try:
                        total += _mask_paragraph(para, model, lm_studio_url)
                    except Exception as e:
                        errors.append(f"table cell: {e}")

    doc.save(output)
    return ProcessResult(output_path=output, total_replacements=total, errors=errors)
