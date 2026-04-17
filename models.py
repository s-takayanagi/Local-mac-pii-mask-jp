from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MaskResult:
    final_text: str
    replacements: list[dict]
    confidence: float
    error: str | None = None


@dataclass
class MaskerResult:
    masked_text: str
    replacements: list[dict] = field(default_factory=list)


@dataclass
class ReviewerResult:
    final_text: str
    additional: list[dict] = field(default_factory=list)
    confidence: float = 0.9


@dataclass
class ProcessResult:
    output_path: Path
    total_replacements: int
    errors: list[str] = field(default_factory=list)
