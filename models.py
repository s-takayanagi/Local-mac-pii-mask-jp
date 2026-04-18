from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MaskResult:
    final_text: str
    replacements: list[dict]
    confidence: float
    error: str | None = None
    layer_counts: dict = field(default_factory=dict)
    # keys: "layer1", "layer2", "layer3", "layer4" → int (件数)


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
    layer_totals: dict = field(default_factory=dict)
    # keys: "layer1"〜"layer4" → ファイル全体の合計件数
    replacements_log: list[dict] = field(default_factory=list)
    # each entry: {"location": str, "original": str, "tag": str, "layer": str}
    warnings: list[str] = field(default_factory=list)
    # 未マスクの可能性がある箇所の警告メッセージ
