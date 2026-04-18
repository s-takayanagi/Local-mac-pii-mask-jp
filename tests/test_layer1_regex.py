import sys
sys.path.insert(0, ".")

from core.layer1_regex import apply_regex


def test_phone_mobile():
    text, reps = apply_regex("090-1234-5678")
    assert text == "[電話番号]"
    assert reps[0]["tag"] == "[電話番号]"


def test_email():
    text, reps = apply_regex("yamada.taro@example.com")
    assert text == "[メール]"


def test_postal_code():
    text, reps = apply_regex("〒150-0001")
    assert "[郵便番号]" in text


def test_url():
    text, _ = apply_regex("https://example.com/path")
    assert text == "[URL]"


def test_combined():
    raw = "山田太郎,yamada.taro@example.com,090-1234-5678,東京都渋谷区1-2-3"
    text, reps = apply_regex(raw)
    assert "[メール]" in text
    assert "[電話番号]" in text
    assert len(reps) >= 2


# --- 追加テストケース ---

def test_phone_landline():
    text, reps = apply_regex("03-1234-5678")
    assert "[電話番号]" in text
    assert any(r["tag"] == "[電話番号]" for r in reps)


def test_phone_fullwidth_hyphen():
    text, reps = apply_regex("090−1234−5678")
    assert "[電話番号]" in text


def test_birth_date():
    text, reps = apply_regex("1990年3月15日")
    assert text == "[生年月日]"
    assert reps[0]["tag"] == "[生年月日]"


def test_birth_date_with_spaces():
    text, reps = apply_regex("1990年 3月 15日")
    assert "[生年月日]" in text


def test_12digit_id():
    text, reps = apply_regex("123456789012")
    assert text == "[識別番号]"
    assert reps[0]["tag"] == "[識別番号]"


def test_11digit_not_masked():
    text, _ = apply_regex("12345678901")
    assert "[識別番号]" not in text


def test_13digit_not_masked():
    text, _ = apply_regex("1234567890123")
    assert "[識別番号]" not in text


def test_excluded_tags_phone():
    # 電話番号タグが除外されても他のパターン（郵便番号等）は動作するため、
    # [電話番号] タグが付与されないことのみ検証する
    text, reps = apply_regex("090-1234-5678", excluded_tags={"[電話番号]"})
    assert "[電話番号]" not in text
    assert not any(r["tag"] == "[電話番号]" for r in reps)


def test_excluded_tags_email():
    text, reps = apply_regex("test@example.com", excluded_tags={"[メール]"})
    assert "[メール]" not in text
    assert "test@example.com" in text


def test_empty_string():
    text, reps = apply_regex("")
    assert text == ""
    assert reps == []


def test_postal_code_without_kigou():
    text, reps = apply_regex("郵便番号は150-0001です")
    assert "[郵便番号]" in text


def test_multiple_pii_in_text():
    text, reps = apply_regex("test@example.com と 090-1234-5678 が含まれる")
    assert "[メール]" in text
    assert "[電話番号]" in text
    assert len(reps) >= 2


def test_replacement_contains_original():
    text, reps = apply_regex("090-1234-5678")
    assert reps[0]["original"] == "090-1234-5678"
