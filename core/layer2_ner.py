from __future__ import annotations

_nlp = None

_ADMIN_PREFIXES = (
    "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島",
    "茨城", "栃木", "群馬", "埼玉", "千葉", "東京", "神奈川",
    "新潟", "富山", "石川", "福井", "山梨", "長野", "岐阜",
    "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫",
    "奈良", "和歌山", "鳥取", "島根", "岡山", "広島", "山口",
    "徳島", "香川", "愛媛", "高知", "福岡", "佐賀", "長崎",
    "熊本", "大分", "宮崎", "鹿児島", "沖縄",
)

_LABEL_TAG: dict[str, str] = {
    "Person": "[氏名]",
    "PERSON": "[氏名]",
    "City": "[住所]",
    "Province": "[住所]",
    "Address": "[住所]",
    "Organization": "[会社名]",
    "Company": "[会社名]",
    "Phone": "[電話番号]",
    "Email": "[メール]",
}


def _load_nlp():
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.load("ja_ginza_electra")
    return _nlp


def _is_admin_unit(text: str) -> bool:
    return any(text.startswith(p) for p in _ADMIN_PREFIXES)


def apply_ner(text: str) -> tuple[str, list[dict]]:
    nlp = _load_nlp()
    doc = nlp(text)
    replacements: list[dict] = []

    spans: list[tuple[int, int, str]] = []
    for ent in doc.ents:
        tag = _LABEL_TAG.get(ent.label_)
        if tag is None:
            continue
        if tag == "[住所]" and _is_admin_unit(ent.text):
            continue
        spans.append((ent.start_char, ent.end_char, tag))
        replacements.append({"original": ent.text, "tag": tag})

    # 後ろから置換して文字位置がずれないようにする
    result = text
    for start, end, tag in sorted(spans, key=lambda x: x[0], reverse=True):
        result = result[:start] + tag + result[end:]

    return result, replacements
