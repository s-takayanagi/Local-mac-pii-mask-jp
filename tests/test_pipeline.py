import sys
sys.path.insert(0, ".")

from unittest.mock import patch, MagicMock

from core.pipeline import mask_text
from models import MaskResult


_MODEL = "test-model"
_URL = "http://localhost:1234/v1/chat/completions"


def _regex_passthrough(text, excluded_tags=None):
    return text, []


def _ner_passthrough(text, excluded_tags=None):
    return text, []


def _masker_result(text):
    return {"masked_text": text, "replacements": []}


def _reviewer_result(text):
    return {"final_text": text, "additional": [], "confidence": 0.95}


# --- 空・短文の早期リターン ---

def test_empty_text_returns_as_is():
    result = mask_text("", _MODEL, _URL)
    assert result.final_text == ""
    assert result.replacements == []
    assert result.confidence == 1.0


def test_single_char_returns_as_is():
    result = mask_text("A", _MODEL, _URL)
    assert result.final_text == "A"


def test_whitespace_only_returns_as_is():
    result = mask_text("   ", _MODEL, _URL)
    assert result.final_text == "   "


# --- Layer 1 のみ有効 ---

def test_layer1_only():
    with (
        patch("core.pipeline.apply_regex", return_value=("[電話番号]", [{"original": "090-1234-5678", "tag": "[電話番号]"}])) as mock_l1,
        patch("core.pipeline.apply_ner") as mock_l2,
        patch("core.pipeline.call_masker") as mock_l3,
        patch("core.pipeline.call_reviewer") as mock_l4,
    ):
        result = mask_text("090-1234-5678", _MODEL, _URL, enabled_layers={"layer1"})

    mock_l1.assert_called_once()
    mock_l2.assert_not_called()
    mock_l3.assert_not_called()
    mock_l4.assert_not_called()
    assert "[電話番号]" in result.final_text
    assert result.layer_counts["layer1"] == 1
    assert result.layer_counts["layer2"] == 0


def test_layer2_only():
    with (
        patch("core.pipeline.apply_regex") as mock_l1,
        patch("core.pipeline.apply_ner", return_value=("[氏名]が来た", [{"original": "山田太郎", "tag": "[氏名]"}])) as mock_l2,
        patch("core.pipeline.call_masker") as mock_l3,
        patch("core.pipeline.call_reviewer") as mock_l4,
    ):
        result = mask_text("山田太郎が来た", _MODEL, _URL, enabled_layers={"layer2"})

    mock_l1.assert_not_called()
    mock_l2.assert_called_once()
    mock_l3.assert_not_called()
    mock_l4.assert_not_called()
    assert "[氏名]" in result.final_text
    assert result.layer_counts["layer2"] == 1


# --- LLM レイヤー ---

def test_all_layers_success():
    with (
        patch("core.pipeline.apply_regex", return_value=("[電話番号]", [{"original": "090-1234-5678", "tag": "[電話番号]"}])),
        patch("core.pipeline.apply_ner", return_value=("[電話番号]", [])),
        patch("core.pipeline.call_masker", return_value={"masked_text": "[電話番号]", "replacements": []}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "[電話番号]", "additional": [], "confidence": 0.98}),
    ):
        result = mask_text("090-1234-5678", _MODEL, _URL)

    assert result.final_text == "[電話番号]"
    assert result.confidence == 0.98
    assert result.error is None


def test_layer3_failure_returns_l1_l2_result():
    with (
        patch("core.pipeline.apply_regex", return_value=("[電話番号]", [{"original": "090-1234-5678", "tag": "[電話番号]"}])),
        patch("core.pipeline.apply_ner", return_value=("[電話番号]", [])),
        patch("core.pipeline.call_masker", return_value=None),
    ):
        result = mask_text("090-1234-5678", _MODEL, _URL)

    assert result.final_text == "[電話番号]"
    assert result.confidence == 0.7
    assert result.error is not None
    assert "Layer 3" in result.error


def test_layer4_failure_returns_layer3_result():
    with (
        patch("core.pipeline.apply_regex", return_value=("[電話番号]", [{"original": "090-1234-5678", "tag": "[電話番号]"}])),
        patch("core.pipeline.apply_ner", return_value=("[電話番号]", [])),
        patch("core.pipeline.call_masker", return_value={"masked_text": "[電話番号]", "replacements": []}),
        patch("core.pipeline.call_reviewer", return_value=None),
    ):
        result = mask_text("090-1234-5678", _MODEL, _URL)

    assert result.final_text == "[電話番号]"
    assert result.confidence == 0.8
    assert result.error is not None
    assert "Layer 4" in result.error


# --- excluded_tags の伝播 ---

def test_excluded_tags_passed_to_layer1():
    with (
        patch("core.pipeline.apply_regex", return_value=("090-1234-5678", [])) as mock_l1,
        patch("core.pipeline.apply_ner", return_value=("090-1234-5678", [])),
        patch("core.pipeline.call_masker", return_value={"masked_text": "090-1234-5678", "replacements": []}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "090-1234-5678", "additional": [], "confidence": 1.0}),
    ):
        mask_text("090-1234-5678", _MODEL, _URL, excluded_tags={"[電話番号]"})

    call_args = mock_l1.call_args
    assert "[電話番号]" in call_args[0][1] or "[電話番号]" in (call_args[1].get("excluded_tags") or set())


def test_excluded_tags_passed_to_layer2():
    with (
        patch("core.pipeline.apply_regex", return_value=("山田太郎", [])),
        patch("core.pipeline.apply_ner", return_value=("山田太郎", [])) as mock_l2,
        patch("core.pipeline.call_masker", return_value={"masked_text": "山田太郎", "replacements": []}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "山田太郎", "additional": [], "confidence": 1.0}),
    ):
        mask_text("山田太郎", _MODEL, _URL, excluded_tags={"[氏名]"})

    call_args = mock_l2.call_args
    excluded = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("excluded_tags")
    assert "[氏名]" in excluded


# --- layer_counts の正確性 ---

def test_layer_counts_accuracy():
    with (
        patch("core.pipeline.apply_regex", return_value=("x", [{"original": "a", "tag": "[メール]"}, {"original": "b", "tag": "[電話番号]"}])),
        patch("core.pipeline.apply_ner", return_value=("x", [{"original": "c", "tag": "[氏名]"}])),
        patch("core.pipeline.call_masker", return_value={"masked_text": "x", "replacements": [{"original": "d", "tag": "[会社名]"}]}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "x", "additional": [{"original": "e", "tag": "[住所]"}], "confidence": 0.9}),
    ):
        result = mask_text("テスト文字列", _MODEL, _URL)

    assert result.layer_counts["layer1"] == 2
    assert result.layer_counts["layer2"] == 1
    assert result.layer_counts["layer3"] == 1
    assert result.layer_counts["layer4"] == 1


# --- NER 例外時のフォールバック ---

def test_ner_exception_falls_back_gracefully():
    with (
        patch("core.pipeline.apply_regex", return_value=("[電話番号]", [{"original": "090-1234-5678", "tag": "[電話番号]"}])),
        patch("core.pipeline.apply_ner", side_effect=RuntimeError("NER モデルが見つかりません")),
        patch("core.pipeline.call_masker", return_value={"masked_text": "[電話番号]", "replacements": []}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "[電話番号]", "additional": [], "confidence": 0.9}),
    ):
        result = mask_text("090-1234-5678", _MODEL, _URL)

    # NER 失敗してもパイプラインが完走すること
    assert result.final_text is not None
    # layer2 エラー情報がある場合は error フィールドに含まれる
    assert result.layer_counts.get("layer2", 0) == 0


# --- replacements の layer フィールド ---

def test_replacements_have_layer_field():
    with (
        patch("core.pipeline.apply_regex", return_value=("x", [{"original": "a", "tag": "[メール]"}])),
        patch("core.pipeline.apply_ner", return_value=("x", [{"original": "b", "tag": "[氏名]"}])),
        patch("core.pipeline.call_masker", return_value={"masked_text": "x", "replacements": [{"original": "c", "tag": "[会社名]"}]}),
        patch("core.pipeline.call_reviewer", return_value={"final_text": "x", "additional": [{"original": "d", "tag": "[住所]"}], "confidence": 0.9}),
    ):
        result = mask_text("テスト文字列", _MODEL, _URL)

    layers = {r["layer"] for r in result.replacements}
    assert layers == {"layer1", "layer2", "layer3", "layer4"}
