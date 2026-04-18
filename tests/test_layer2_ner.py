import sys
sys.path.insert(0, ".")

from unittest.mock import MagicMock, patch

import core.layer2_ner as ner_module
from core.layer2_ner import apply_ner, _is_admin_unit


class _MockEnt:
    def __init__(self, text, label_, start_char, end_char):
        self.text = text
        self.label_ = label_
        self.start_char = start_char
        self.end_char = end_char


class _MockDoc:
    def __init__(self, ents):
        self.ents = ents


def _make_mock_nlp(*ents):
    mock_nlp = MagicMock()
    mock_nlp.return_value = _MockDoc(list(ents))
    return mock_nlp


def _patch_nlp(*ents):
    return patch.object(ner_module, "_load_nlp", return_value=_make_mock_nlp(*ents))


# --- _is_admin_unit のテスト ---

def test_is_admin_unit_tokyo():
    assert _is_admin_unit("東京都") is True


def test_is_admin_unit_osaka():
    # "大阪" が ADMIN_PREFIXES に含まれるため "大阪府" もマッチする
    assert _is_admin_unit("大阪府") is True


def test_is_admin_unit_osaka_prefix():
    assert _is_admin_unit("大阪") is True


def test_is_admin_unit_hokkaido():
    assert _is_admin_unit("北海道") is True


def test_is_admin_unit_not_admin():
    assert _is_admin_unit("渋谷区") is False


def test_is_admin_unit_empty():
    assert _is_admin_unit("") is False


# --- apply_ner のテスト ---

def test_person_masked():
    ent = _MockEnt("山田太郎", "Person", 0, 4)
    with _patch_nlp(ent):
        text, reps = apply_ner("山田太郎が連絡してきた")
    assert "[氏名]" in text
    assert any(r["tag"] == "[氏名]" for r in reps)


def test_person_label_uppercase():
    ent = _MockEnt("Yamada Taro", "PERSON", 0, 11)
    with _patch_nlp(ent):
        text, reps = apply_ner("Yamada Taro called")
    assert "[氏名]" in text


def test_address_masked():
    ent = _MockEnt("渋谷区1-2-3", "Address", 3, 11)
    with _patch_nlp(ent):
        text, reps = apply_ner("東京都渋谷区1-2-3")
    assert "[住所]" in text
    assert any(r["tag"] == "[住所]" for r in reps)


def test_city_label_masked():
    ent = _MockEnt("渋谷区", "City", 0, 3)
    with _patch_nlp(ent):
        text, reps = apply_ner("渋谷区在住")
    assert "[住所]" in text


def test_province_masked_if_not_admin():
    # "千代田区" は都道府県ではないのでマスクされる
    ent = _MockEnt("千代田区", "Province", 0, 4)
    with _patch_nlp(ent):
        text, reps = apply_ner("千代田区の住所")
    assert "[住所]" in text


def test_admin_unit_not_masked():
    ent = _MockEnt("東京都", "Province", 0, 3)
    with _patch_nlp(ent):
        text, reps = apply_ner("東京都在住の方")
    assert "[住所]" not in text
    assert reps == []


def test_organization_masked():
    ent = _MockEnt("株式会社サンプル", "Organization", 0, 8)
    with _patch_nlp(ent):
        text, reps = apply_ner("株式会社サンプル社員")
    assert "[会社名]" in text
    assert any(r["tag"] == "[会社名]" for r in reps)


def test_company_label_masked():
    ent = _MockEnt("サンプル社", "Company", 0, 4)
    with _patch_nlp(ent):
        text, reps = apply_ner("サンプル社のスタッフ")
    assert "[会社名]" in text


def test_excluded_tags_person():
    ent = _MockEnt("山田太郎", "Person", 0, 4)
    with _patch_nlp(ent):
        text, reps = apply_ner("山田太郎が来た", excluded_tags={"[氏名]"})
    assert "[氏名]" not in text
    assert reps == []


def test_excluded_tags_address():
    ent = _MockEnt("渋谷区1-2-3", "Address", 0, 8)
    with _patch_nlp(ent):
        text, reps = apply_ner("渋谷区1-2-3です", excluded_tags={"[住所]"})
    assert "[住所]" not in text
    assert reps == []


def test_empty_string():
    with _patch_nlp():
        text, reps = apply_ner("")
    assert text == ""
    assert reps == []


def test_unknown_label_ignored():
    ent = _MockEnt("何かのもの", "UnknownLabel", 0, 5)
    with _patch_nlp(ent):
        text, reps = apply_ner("何かのものがある")
    # タグなし、置換なし
    assert reps == []
    assert "[" not in text


def test_multiple_entities_masked():
    ents = [
        _MockEnt("山田太郎", "Person", 0, 4),
        _MockEnt("株式会社サンプル", "Organization", 5, 13),
    ]
    with _patch_nlp(*ents):
        text, reps = apply_ner("山田太郎 株式会社サンプル")
    assert "[氏名]" in text
    assert "[会社名]" in text
    assert len(reps) == 2


def test_replacement_log_has_original():
    ent = _MockEnt("山田太郎", "Person", 0, 4)
    with _patch_nlp(ent):
        _, reps = apply_ner("山田太郎です")
    assert reps[0]["original"] == "山田太郎"
