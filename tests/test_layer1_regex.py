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
