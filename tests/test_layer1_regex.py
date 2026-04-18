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


# --- 電話番号 ---

def test_phone_landline():
    text, reps = apply_regex("03-1234-5678")
    assert "[電話番号]" in text
    assert any(r["tag"] == "[電話番号]" for r in reps)


def test_phone_fullwidth_hyphen():
    text, reps = apply_regex("090−1234−5678")
    assert "[電話番号]" in text


# --- メールアドレス (.co.jp 形式) ---

def test_email_co_jp():
    text, reps = apply_regex("ito.seiichi@alpha-sys.co.jp")
    assert text == "[メール]"
    assert reps[0]["original"] == "ito.seiichi@alpha-sys.co.jp"


def test_email_co_jp_in_sentence():
    text, _ = apply_regex("連絡先: yamada.taro@example-corp.co.jp まで")
    assert "[メール]" in text
    assert ".co.jp" not in text


def test_email_standard_domain():
    text, _ = apply_regex("test@example.com")
    assert text == "[メール]"


# --- 識別番号 ---

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


# --- 生年月日パターン削除の確認 ---

def test_date_not_masked():
    """生年月日タグ廃止後は日付がマスクされない"""
    text, reps = apply_regex("1990年3月15日")
    assert "[生年月日]" not in text
    assert text == "1990年3月15日"
    assert reps == []


def test_meeting_date_not_masked():
    text, reps = apply_regex("2024年10月15日の会議")
    assert "[生年月日]" not in text
    assert reps == []


# --- URL（全角文字で打ち切り） ---

def test_url_stops_at_fullwidth_char():
    text, reps = apply_regex("利用規約（https://example.com/terms）に同意")
    assert "[URL]" in text
    # 全角括弧や日本語がマスク範囲に含まれないこと
    assert "）" not in reps[0]["original"]
    assert "に同意" not in reps[0]["original"]


def test_url_ascii_only():
    text, _ = apply_regex("https://example.com/path?q=1&page=2")
    assert text == "[URL]"


# --- excluded_tags ---

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


# --- 住所 ---

def test_address_full_with_building():
    text, reps = apply_regex("東京都渋谷区代々木1-2-3 代々木マンション401")
    assert "[住所]" in text
    assert any(r["tag"] == "[住所]" for r in reps)


def test_address_without_building():
    text, reps = apply_regex("大阪府大阪市北区梅田1-1-1")
    assert "[住所]" in text
    assert any(r["tag"] == "[住所]" for r in reps)


def test_address_with_postal_code():
    text, reps = apply_regex("〒150-0001 東京都渋谷区神宮前1-2-3")
    assert "[郵便番号]" in text
    assert "[住所]" in text


def test_prefecture_only_not_masked():
    text, reps = apply_regex("東京都在住")
    assert "[住所]" not in text


# --- エッジケース ---

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
