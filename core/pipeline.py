import logging
import time

from models import MaskResult
from core.layer1_regex import apply_regex
from core.layer2_ner import apply_ner
from core.layer3_llm import call_masker, call_reviewer

logger = logging.getLogger(__name__)

_ALL_LAYERS = {"layer1", "layer2", "layer3", "layer4"}


def mask_text(
    text: str,
    model: str,
    lm_studio_url: str,
    enabled_layers: set[str] | None = None,
    excluded_tags: set[str] | None = None,
) -> MaskResult:
    if not text or not text.strip() or len(text.strip()) <= 1:
        return MaskResult(final_text=text, replacements=[], confidence=1.0)

    enabled = enabled_layers if enabled_layers is not None else _ALL_LAYERS

    preview = text[:80].replace("\n", " ")
    logger.debug("パイプライン開始 | 入力文字数=%d | 先頭='%s'", len(text), preview)

    layer_elapsed: dict[str, float] = {}

    # Layer 1: 正規表現
    l1_reps: list[dict] = []
    if "layer1" in enabled:
        t0 = time.monotonic()
        logger.info("[Layer 1] 正規表現マスキング 開始")
        l1_text, l1_reps = apply_regex(text, excluded_tags)
        elapsed = time.monotonic() - t0
        layer_elapsed["layer1"] = elapsed
        logger.info("[Layer 1] 完了 | 検出=%d件 | 経過=%.3fs", len(l1_reps), elapsed)
        for r in l1_reps:
            logger.debug("[Layer 1] '%s' → '%s'", r.get("original"), r.get("tag"))
    else:
        logger.info("[Layer 1] スキップ（無効）")
        l1_text = text

    # Layer 2: NER
    l2_reps: list[dict] = []
    l2_error: str | None = None
    if "layer2" in enabled:
        t0 = time.monotonic()
        logger.info("[Layer 2] 固有名詞認識 (NER) 開始")
        try:
            l2_text, l2_reps = apply_ner(l1_text, excluded_tags)
            elapsed = time.monotonic() - t0
            layer_elapsed["layer2"] = elapsed
            logger.info("[Layer 2] 完了 | 検出=%d件 | 経過=%.3fs", len(l2_reps), elapsed)
            for r in l2_reps:
                logger.debug("[Layer 2] '%s' → '%s'", r.get("original"), r.get("tag"))
        except Exception as e:
            layer_elapsed["layer2"] = time.monotonic() - t0
            logger.error("[Layer 2] NER 失敗 | %s", e)
            l2_text, l2_reps = l1_text, []
            l2_error = str(e)
    else:
        logger.info("[Layer 2] スキップ（無効）")
        l2_text = l1_text

    # Layer 3: LLM マスキング
    l3_reps: list[dict] = []
    masked = l2_text
    if "layer3" in enabled:
        logger.info("[Layer 3] LLM マスキング 開始")
        t0 = time.monotonic()
        masker_result = call_masker(l2_text, model, lm_studio_url, excluded_tags)
        elapsed = time.monotonic() - t0
        layer_elapsed["layer3"] = elapsed
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
                layer_elapsed=layer_elapsed,
            )
        l3_reps = masker_result.get("replacements", [])
        if not isinstance(l3_reps, list):
            l3_reps = []
        logger.info("[Layer 3] 完了 | 検出=%d件 | 経過=%.3fs", len(l3_reps), elapsed)
        for r in l3_reps:
            logger.debug("[Layer 3] '%s' → '%s'", r.get("original"), r.get("tag"))
        masked_val = masker_result.get("masked_text", l2_text)
        masked = masked_val if isinstance(masked_val, str) and masked_val else l2_text
    else:
        logger.info("[Layer 3] スキップ（無効）")

    # Layer 4: LLM レビュー
    additional: list[dict] = []
    confidence = 1.0
    final = masked
    if "layer4" in enabled:
        logger.info("[Layer 4] LLM レビュー 開始")
        t0 = time.monotonic()
        reviewer_result = call_reviewer(masked, model, lm_studio_url, excluded_tags, original_text=text)
        elapsed = time.monotonic() - t0
        layer_elapsed["layer4"] = elapsed
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
                layer_elapsed=layer_elapsed,
            )
        additional = reviewer_result.get("additional", [])
        if not isinstance(additional, list):
            additional = []
        confidence = reviewer_result.get("confidence", 0.9)
        if not isinstance(confidence, (int, float)):
            confidence = 0.9
        final_val = reviewer_result.get("final_text", masked)
        final = final_val if isinstance(final_val, str) and final_val else masked
        logger.info(
            "[Layer 4] 完了 | 追加検出=%d件 | confidence=%.2f | 経過=%.3fs",
            len(additional), confidence, elapsed,
        )
        for r in additional:
            logger.debug("[Layer 4] '%s' → '%s'", r.get("original"), r.get("tag"))
    else:
        logger.info("[Layer 4] スキップ（無効）")

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
        layer_elapsed=layer_elapsed,
    )
