import logging
import time

from models import MaskResult
from core.layer1_regex import apply_regex
from core.layer2_ner import apply_ner
from core.layer3_llm import call_masker, call_reviewer

logger = logging.getLogger(__name__)


def mask_text(text: str, model: str, lm_studio_url: str) -> MaskResult:
    if not text or not text.strip() or len(text.strip()) <= 1:
        return MaskResult(final_text=text, replacements=[], confidence=1.0)

    preview = text[:80].replace("\n", " ")
    logger.debug("パイプライン開始 | 入力文字数=%d | 先頭='%s'", len(text), preview)

    # Layer 1: 正規表現
    t0 = time.monotonic()
    logger.info("[Layer 1] 正規表現マスキング 開始")
    l1_text, l1_reps = apply_regex(text)
    logger.info("[Layer 1] 完了 | 検出=%d件 | 経過=%.3fs", len(l1_reps), time.monotonic() - t0)
    for r in l1_reps:
        logger.debug("[Layer 1] '%s' → '%s'", r.get("original"), r.get("tag"))

    # Layer 2: NER
    t0 = time.monotonic()
    logger.info("[Layer 2] 固有名詞認識 (NER) 開始")
    l2_error: str | None = None
    try:
        l2_text, l2_reps = apply_ner(l1_text)
        logger.info("[Layer 2] 完了 | 検出=%d件 | 経過=%.3fs", len(l2_reps), time.monotonic() - t0)
        for r in l2_reps:
            logger.debug("[Layer 2] '%s' → '%s'", r.get("original"), r.get("tag"))
    except Exception as e:
        logger.error("[Layer 2] NER 失敗 | %s", e)
        l2_text, l2_reps = l1_text, []
        l2_error = str(e)

    # Layer 3: LLM マスキング
    logger.info("[Layer 3] LLM マスキング 開始")
    t0 = time.monotonic()
    masker_result = call_masker(l2_text, model, lm_studio_url)
    if masker_result is None:
        logger.warning("[Layer 3] 失敗 — Layer 1+2 の結果で返却")
        errors = []
        if l2_error:
            errors.append(f"Layer 2 NER: {l2_error}")
        errors.append("Layer 3 LLM Masker: 応答なし（接続・モデル名を確認してください）")
        return MaskResult(
            final_text=l2_text,
            replacements=(
                [{**r, "layer": "layer1"} for r in l1_reps] +
                [{**r, "layer": "layer2"} for r in l2_reps]
            ),
            confidence=0.7,
            error="; ".join(errors),
            layer_counts={"layer1": len(l1_reps), "layer2": len(l2_reps), "layer3": 0, "layer4": 0},
        )

    l3_reps = masker_result.get("replacements", [])
    logger.info("[Layer 3] 完了 | 検出=%d件 | 経過=%.3fs", len(l3_reps), time.monotonic() - t0)
    for r in l3_reps:
        logger.debug("[Layer 3] '%s' → '%s'", r.get("original"), r.get("tag"))
    masked = masker_result.get("masked_text", l2_text)

    # Layer 4: LLM レビュー
    logger.info("[Layer 4] LLM レビュー 開始")
    t0 = time.monotonic()
    reviewer_result = call_reviewer(masked, model, lm_studio_url)
    if reviewer_result is None:
        logger.warning("[Layer 4] 失敗 — Masker 結果で返却")
        errors = []
        if l2_error:
            errors.append(f"Layer 2 NER: {l2_error}")
        errors.append("Layer 4 LLM Reviewer: 応答なし")
        return MaskResult(
            final_text=masked,
            replacements=(
                [{**r, "layer": "layer1"} for r in l1_reps] +
                [{**r, "layer": "layer2"} for r in l2_reps] +
                [{**r, "layer": "layer3"} for r in l3_reps]
            ),
            confidence=0.8,
            error="; ".join(errors),
            layer_counts={"layer1": len(l1_reps), "layer2": len(l2_reps), "layer3": len(l3_reps), "layer4": 0},
        )

    additional = reviewer_result.get("additional", [])
    confidence = reviewer_result.get("confidence", 0.9)
    final = reviewer_result.get("final_text", masked)
    logger.info(
        "[Layer 4] 完了 | 追加検出=%d件 | confidence=%.2f | 経過=%.3fs",
        len(additional), confidence, time.monotonic() - t0,
    )
    for r in additional:
        logger.debug("[Layer 4] '%s' → '%s'", r.get("original"), r.get("tag"))

    errors = [f"Layer 2 NER: {l2_error}"] if l2_error else []
    return MaskResult(
        final_text=final,
        replacements=(
            [{**r, "layer": "layer1"} for r in l1_reps] +
            [{**r, "layer": "layer2"} for r in l2_reps] +
            [{**r, "layer": "layer3"} for r in l3_reps] +
            [{**r, "layer": "layer4"} for r in additional]
        ),
        confidence=confidence,
        error="; ".join(errors) if errors else None,
        layer_counts={
            "layer1": len(l1_reps),
            "layer2": len(l2_reps),
            "layer3": len(l3_reps),
            "layer4": len(additional),
        },
    )
