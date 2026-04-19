import sys
sys.path.insert(0, ".")

import json
from unittest.mock import MagicMock, patch
import requests

from core.layer3_llm import call_masker, call_reviewer, _revert_excluded, _is_lfm2_model, _apply_lfm2_entities, LFM2_SYSTEM


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


def test_call_reviewer_additional_none_tolerated():
    # additional=None が返っても call_reviewer 内で空リストに正規化される
    body = {"final_text": "[氏名]", "additional": None, "confidence": 0.9}
    with patch("requests.post", return_value=_make_response(body)):
        result = call_reviewer("[氏名]", "test-model", "http://localhost:1234/v1/chat/completions")
    assert result is not None
    assert result["final_text"] == "[氏名]"
    assert result["additional"] == []


# --- LFM2 モード ---

def test_is_lfm2_model_detected():
    assert _is_lfm2_model("lfm2-350m-pii-extract-jp") is True
    assert _is_lfm2_model("LFM2-350M-PII-Extract-JP") is True
    assert _is_lfm2_model("LFM2-1B-PII-Extract-JP") is True


def test_is_lfm2_model_not_detected():
    assert _is_lfm2_model("qwen2.5-7b-instruct") is False
    assert _is_lfm2_model("gpt-4o") is False
    assert _is_lfm2_model("pii-extract-custom") is False


def test_apply_lfm2_entities_masks_correctly():
    raw = {"human_name": ["山田太郎"], "company_name": ["株式会社サンプル"]}
    masked, reps = _apply_lfm2_entities("山田太郎 株式会社サンプル", raw, set())
    assert "[氏名]" in masked
    assert "[会社名]" in masked
    assert any(r["tag"] == "[氏名]" for r in reps)
    assert any(r["tag"] == "[会社名]" for r in reps)


def test_apply_lfm2_entities_substring_longer_first():
    """部分文字列（田中）と長い文字列（田中太郎）が同時に返っても正しく処理される"""
    raw = {"human_name": ["田中", "田中太郎"]}
    masked, reps = _apply_lfm2_entities("田中太郎と田中さん", raw, set())
    # "田中太郎" が先に置換されるため "[氏名]と[氏名]さん" になる
    assert masked == "[氏名]と[氏名]さん"
    assert len(reps) == 2


def test_apply_lfm2_entities_multiple_occurrences():
    """同じエンティティが複数回出現する場合、すべて置換される"""
    raw = {"human_name": ["山田太郎"]}
    masked, reps = _apply_lfm2_entities("山田太郎さんと山田太郎さん", raw, set())
    assert masked == "[氏名]さんと[氏名]さん"
    assert len(reps) == 2


def test_revert_excluded_ordering_with_reference_text():
    """replacements の順序が逆でも reference_text で正しく元に戻せる"""
    # 本文順: 山田 → 田中
    reference = "山田さんと田中さん"
    # replacements は逆順で来た想定
    reps = [
        {"original": "田中", "tag": "[氏名]"},
        {"original": "山田", "tag": "[氏名]"},
    ]
    reverted, kept = _revert_excluded(
        "[氏名]さんと[氏名]さん", reps, {"[氏名]"}, reference_text=reference
    )
    assert reverted == "山田さんと田中さん"
    assert kept == []


def test_apply_lfm2_entities_excluded_tags():
    raw = {"human_name": ["山田太郎"], "phone_number": ["090-1234-5678"]}
    masked, reps = _apply_lfm2_entities("山田太郎 090-1234-5678", raw, {"[電話番号]"})
    assert "[氏名]" in masked
    assert "090-1234-5678" in masked
    assert not any(r["tag"] == "[電話番号]" for r in reps)


def test_call_masker_lfm2_mode():
    body = {"human_name": ["山田太郎"], "email_address": ["test@example.com"], "company_name": []}
    with patch("requests.post", return_value=_make_response(body)) as mock_post:
        result = call_masker(
            "山田太郎のメール: test@example.com",
            "lfm2-350m-pii-extract-jp",
            "http://localhost:1234/v1/chat/completions",
        )
    assert result is not None
    assert "[氏名]" in result["masked_text"]
    assert "[メール]" in result["masked_text"]
    assert any(r["tag"] == "[氏名]" for r in result["replacements"])
    # LFM2 専用システムプロンプトが使われていること
    sent_payload = mock_post.call_args[1]["json"]
    assert sent_payload["messages"][0]["content"] == LFM2_SYSTEM
    # temperature=0 で呼ばれていること
    assert sent_payload["temperature"] == 0


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


# --- 位置追跡: 部分文字列競合の回避 ---

def test_lfm2_substring_does_not_corrupt_longer_match():
    """短い『田中』が長い『田中太郎』の中身を奪わないこと"""
    raw = {"human_name": ["田中太郎", "田中"]}
    masked, reps = _apply_lfm2_entities("田中太郎と田中が会う", raw, set())
    # 両者とも別個にマスクされる（田中太郎→[氏名]、田中→[氏名]）
    assert masked == "[氏名]と[氏名]が会う"
    assert len(reps) == 2
    # 出現順: 田中太郎 が先
    assert reps[0]["original"] == "田中太郎"
    assert reps[1]["original"] == "田中"


def test_lfm2_same_entity_multiple_occurrences():
    raw = {"human_name": ["田中"]}
    masked, reps = _apply_lfm2_entities("田中と田中が会議", raw, set())
    assert masked == "[氏名]と[氏名]が会議"
    assert len(reps) == 2
    assert all(r["original"] == "田中" for r in reps)


def test_lfm2_excluded_tag_skipped():
    raw = {"human_name": ["山田"], "phone_number": ["090-1111-2222"]}
    masked, reps = _apply_lfm2_entities(
        "山田 090-1111-2222", raw, {"[氏名]"}
    )
    assert "山田" in masked
    assert "[電話番号]" in masked
    assert all(r["tag"] != "[氏名]" for r in reps)


# --- JSON パース堅牢性 ---

def test_call_masker_handles_extra_trailing_text():
    """JSON の後にゴミが付いていても raw_decode で先頭の JSON を取り出せる"""
    content = (
        '{"masked_text": "[氏名]さん", '
        '"replacements": [{"original": "山田", "tag": "[氏名]"}]}'
        "\nNote: this is extra text }"
    )
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "choices": [{"message": {"content": content}}],
        "usage": {},
    }
    resp.raise_for_status = MagicMock()
    with patch("requests.post", return_value=resp):
        result = call_masker("山田さん", "qwen-test",
                             "http://localhost:1234/v1/chat/completions")
    assert result is not None
    assert result["masked_text"] == "[氏名]さん"
