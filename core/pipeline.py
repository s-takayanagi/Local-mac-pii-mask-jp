from models import MaskResult
from core.layer1_regex import apply_regex
from core.layer2_ner import apply_ner
from core.layer3_llm import call_masker, call_reviewer


def mask_text(text: str, model: str, lm_studio_url: str) -> MaskResult:
    if not text or not text.strip() or len(text.strip()) <= 1:
        return MaskResult(final_text=text, replacements=[], confidence=1.0)

    l1_text, l1_reps = apply_regex(text)
    l2_text, l2_reps = apply_ner(l1_text)

    masker_result = call_masker(l2_text, model, lm_studio_url)
    if masker_result is None:
        return MaskResult(
            final_text=l2_text,
            replacements=l1_reps + l2_reps,
            confidence=0.7,
            error="Masker failed",
        )

    masked = masker_result.get("masked_text", l2_text)

    reviewer_result = call_reviewer(masked, model, lm_studio_url)
    if reviewer_result is None:
        return MaskResult(
            final_text=masked,
            replacements=l1_reps + l2_reps + masker_result.get("replacements", []),
            confidence=0.8,
        )

    final = reviewer_result.get("final_text", masked)
    confidence = reviewer_result.get("confidence", 0.9)
    additional = reviewer_result.get("additional", [])

    all_reps = l1_reps + l2_reps + masker_result.get("replacements", []) + additional
    return MaskResult(final_text=final, replacements=all_reps, confidence=confidence)
