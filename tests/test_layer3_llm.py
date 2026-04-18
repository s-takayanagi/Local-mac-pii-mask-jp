import sys
sys.path.insert(0, ".")

import json
from unittest.mock import MagicMock, patch
import requests

from core.layer3_llm import call_masker, call_reviewer, _revert_excluded, _is_lfm2_model, _apply_lfm2_entities


def _make_response(body: dict, status: int = 200):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {
        "choices": [{"message": {"content": json.dumps(body)}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
    }
    resp.raise_for_status = MagicMock()
    return resp


# --- _revert_excluded のテスト ---

def test_revert_excluded_reverts_tag():
    reps = [{"original": "山田太郎", "tag": "[氏名]"}]
    text, kept = _revert_excluded("[氏名]が来た", reps, {"[氏名]"})
    assert text == "山田太郎が来た"
    assert kept == []


def test_revert_excluded_keeps_non_excluded():
    reps = [
        {"original": "山田太郎", "tag": "[氏名]"},
        {"original": "090-1234-5678", "tag": "[電話番号]"},
    ]
    text, kept = _revert_excluded("[氏名] [電話番号]", reps, {"[氏名]"})
    assert "山田太郎" in text
    assert "[電話番号]" in text
    assert len(kept) == 1
    assert kept[0]["tag"] == "[電話番号]"


def test_revert_excluded_empty_excluded():
    reps = [{"original": "山田太郎", "tag": "[氏名]"}]
    text, kept = _revert_excluded("[氏名]が来た", reps, set())
    assert text == "[氏名]が来た"
    assert len(kept) == 1


# --- call_masker のテスト ---

def test_call_masker_success():
    body = {
        "masked_text": "[氏名]のメール: [メール]",
        "replacements": [
            {"original": "山田太郎", "tag": "[氏名]"},
            {"original": "test@example.com", "tag": "[メール]"},
        ],
    }
    with patch("requests.post", return_value=_make_response(body)):
        result = call_masker("山田太郎のメール: test@example.com", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is not None
    assert result["masked_text"] == "[氏名]のメール: [メール]"
    assert len(result["replacements"]) == 2


def test_call_masker_with_excluded_tags():
    body = {
        "masked_text": "[氏名]のメール: [メール]",
        "replacements": [
            {"original": "山田太郎", "tag": "[氏名]"},
            {"original": "test@example.com", "tag": "[メール]"},
        ],
    }
    with patch("requests.post", return_value=_make_response(body)):
        result = call_masker(
            "山田太郎のメール: test@example.com",
            "test-model",
            "http://localhost:1234/v1/chat/completions",
            excluded_tags={"[氏名]"},
        )
    assert result is not None
    assert "山田太郎" in result["masked_text"]
    assert "[氏名]" not in result["masked_text"]
    assert all(r["tag"] != "[氏名]" for r in result["replacements"])


def test_call_masker_connection_error():
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError("refused")):
        result = call_masker("テスト", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


def test_call_masker_timeout():
    with patch("requests.post", side_effect=requests.exceptions.Timeout()):
        result = call_masker("テスト", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


def test_call_masker_http_error():
    resp = MagicMock()
    resp.status_code = 500
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
    resp.text = "Internal Server Error"
    with patch("requests.post", return_value=resp):
        result = call_masker("テスト", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


def test_call_masker_invalid_json():
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": "これはJSONではありません"}}],
    }
    resp.raise_for_status = MagicMock()
    with patch("requests.post", return_value=resp):
        result = call_masker("テスト", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


def test_call_masker_replacements_not_list_normalized_with_excluded_tags():
    # excluded_tags が指定された場合のみ型チェック・正規化が行われる
    body = {"masked_text": "[氏名]", "replacements": "not_a_list"}
    with patch("requests.post", return_value=_make_response(body)):
        result = call_masker(
            "山田太郎", "test-model", "http://localhost:1234/v1/chat/completions",
            excluded_tags={"[氏名]"},
        )
    assert result is not None
    assert result["replacements"] == []


# --- call_reviewer のテスト ---

def test_call_reviewer_success():
    body = {
        "final_text": "[氏名]のメール: [メール]",
        "additional": [{"original": "残存PII", "tag": "[個人情報]"}],
        "confidence": 0.95,
    }
    with patch("requests.post", return_value=_make_response(body)):
        result = call_reviewer("[氏名]のメール: 残存PII", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is not None
    assert result["final_text"] == "[氏名]のメール: [メール]"
    assert result["confidence"] == 0.95


def test_call_reviewer_with_excluded_tags():
    body = {
        "final_text": "[氏名] [電話番号]",
        "additional": [
            {"original": "山田太郎", "tag": "[氏名]"},
            {"original": "090-1234-5678", "tag": "[電話番号]"},
        ],
        "confidence": 0.9,
    }
    with patch("requests.post", return_value=_make_response(body)):
        result = call_reviewer(
            "[氏名] [電話番号]",
            "test-model",
            "http://localhost:1234/v1/chat/completions",
            excluded_tags={"[電話番号]"},
        )
    assert result is not None
    assert "090-1234-5678" in result["final_text"]
    assert "[電話番号]" not in result["final_text"]


def test_call_reviewer_connection_error():
    with patch("requests.post", side_effect=requests.exceptions.ConnectionError()):
        result = call_reviewer("テスト", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


def test_call_reviewer_additional_none_causes_error():
    # additional=None の場合、_call_lm_studio 内で len(None) エラーが発生し None が返る
    body = {"final_text": "[氏名]", "additional": None, "confidence": 0.9}
    with patch("requests.post", return_value=_make_response(body)):
        result = call_reviewer("[氏名]", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is None


# --- LFM2 モード ---

def test_is_lfm2_model_detected():
    assert _is_lfm2_model("lfm2-350m-pii-extract-jp") is True
    assert _is_lfm2_model("LFM2-350M-PII-Extract-JP") is True
    assert _is_lfm2_model("pii-extract-custom") is True


def test_is_lfm2_model_not_detected():
    assert _is_lfm2_model("qwen2.5-7b-instruct") is False
    assert _is_lfm2_model("gpt-4o") is False


def test_apply_lfm2_entities_masks_correctly():
    raw = {"human_name": ["山田太郎"], "company_name": ["株式会社サンプル"]}
    masked, reps = _apply_lfm2_entities("山田太郎 株式会社サンプル", raw, set())
    assert "[氏名]" in masked
    assert "[会社名]" in masked
    assert any(r["tag"] == "[氏名]" for r in reps)
    assert any(r["tag"] == "[会社名]" for r in reps)


def test_apply_lfm2_entities_excluded_tags():
    raw = {"human_name": ["山田太郎"], "phone_number": ["090-1234-5678"]}
    masked, reps = _apply_lfm2_entities("山田太郎 090-1234-5678", raw, {"[電話番号]"})
    assert "[氏名]" in masked
    assert "090-1234-5678" in masked
    assert not any(r["tag"] == "[電話番号]" for r in reps)


def test_call_masker_lfm2_mode():
    body = {"human_name": ["山田太郎"], "email_address": ["test@example.com"], "company_name": []}
    with patch("requests.post", return_value=_make_response(body)):
        result = call_masker(
            "山田太郎のメール: test@example.com",
            "lfm2-350m-pii-extract-jp",
            "http://localhost:1234/v1/chat/completions",
        )
    assert result is not None
    assert "[氏名]" in result["masked_text"]
    assert "[メール]" in result["masked_text"]
    assert any(r["tag"] == "[氏名]" for r in result["replacements"])


def test_call_reviewer_lfm2_mode():
    body = {"human_name": ["山田太郎"], "address": []}
    with patch("requests.post", return_value=_make_response(body)):
        result = call_reviewer(
            "山田太郎のレポート",
            "lfm2-350m-pii-extract-jp",
            "http://localhost:1234/v1/chat/completions",
        )
    assert result is not None
    assert "[氏名]" in result["final_text"]
    assert result["confidence"] == 0.95
