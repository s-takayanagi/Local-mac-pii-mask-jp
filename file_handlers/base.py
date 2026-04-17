from pathlib import Path
from typing import Protocol
from models import ProcessResult


class FileHandler(Protocol):
    def __call__(self, path: Path, model: str, lm_studio_url: str) -> ProcessResult:
        ...


def masked_output_path(path: Path, suffix: str = "_masked") -> Path:
    return path.with_stem(path.stem + suffix)
