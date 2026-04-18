import logging

from models import MaskResult
from core.layer1_regex import apply_regex
from core.layer2_ner import apply_ner
from core.layer3_llm import call_masker, call_reviewer

logger = logging.getLogger(__name__)


def mask_text(text: str, model: str, lm_studio_url: str) -> MaskResult:
    if not text or not text.strip() or len(text.strip()) <= 1:
        return MaskResult(final_text=text, replacements=[], confidence=1.0)

    # Layer 1: 正規表現
    logger.debug("Layer 1 (正規表現) 開始")
    l1_text, l1_reps = apply_regex(text)
    logger.debug("Layer 1 完了: %d件検出", len(l1_reps))

    # Layer 2: NER
    logger.debug("Layer 2 (NER) 開始")
    l2_error: str | None = None
    try:
        l2_text, l2_reps = apply_ner(l1_text)
        logger.debug("Layer 2 完了: %d件検出", len(l2_reps))
    except Exception as e:
        logger.error("Layer 2 (NER) 失敗: %s", e)
        l2_text, l2_reps = l1_text, []
        l2_error = str(e)

    # Layer 3: LLM マスキング
    logger.debug("Layer 3 (LLM Masker) 開始")
    masker_result = call_masker(l2_text, model, lm_studio_url)
    if masker_result is None:
        logger.warning("Layer 3 (LLM Masker) 失敗 — Layer 1+2 の結果で返却")
        errors = []
        if l2_error:
            errors.append(f"Layer 2 NER: {l2_error}")
        errors.append("Layer 3 LLM Masker: 応答なし（接続・モデル名を確認してください）")
        return MaskResult(
            final_text=l2_text,
            replacements=l1_reps + l2_reps,
            confidence=0.7,
            error="; ".join(errors),
            layer_counts={"layer1": len(l1_reps), "layer2": len(l2_reps), "layer3": 0, "layer4": 0},
        )

    l3_reps = masker_result.get("replacements", [])
    logger.debug("Layer 3 完了: %d件検出", len(l3_reps))
    masked = masker_result.get("masked_text", l2_text)

    # Layer 4: LLM レビュー
    logger.debug("Layer 4 (LLM Reviewer) 開始")
    reviewer_result = call_reviewer(masked, model, lm_studio_url)
    if reviewer_result is None:
        logger.warning("Layer 4 (LLM Reviewer) 失敗 — Masker 結果で返却")
        errors = []
        if l2_error:
            errors.append(f"Layer 2 NER: {l2_error}")
        errors.append("Layer 4 LLM Reviewer: 応答なし")
        return MaskResult(
            final_text=masked,
            replacements=l1_reps + l2_reps + l3_reps,
            confidence=0.8,
            error="; ".join(errors),
            layer_counts={"layer1": len(l1_reps), "layer2": len(l2_reps), "layer3": len(l3_reps), "layer4": 0},
        )

    additional = reviewer_result.get("additional", [])
    confidence = reviewer_result.get("confidence", 0.9)
    final = reviewer_result.get("final_text", masked)
    logger.debug("Layer 4 完了: %d件追加検出, confidence=%.2f", len(additional), confidence)

    errors = [f"Layer 2 NER: {l2_error}"] if l2_error else []
    return MaskResult(
        final_text=final,
        replacements=l1_reps + l2_reps + l3_reps + additional,
        confidence=confidence,
        error="; ".join(errors) if errors else None,
        layer_counts={
            "layer1": len(l1_reps),
            "layer2": len(l2_reps),
            "layer3": len(l3_reps),
            "layer4": len(additional),
        },
    )
