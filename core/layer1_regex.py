import re

# (pattern, tag)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"0[789]0[-−]\d{4}[-−]\d{4}"), "[電話番号]"),
    (re.compile(r"0\d{1,4}[-−]\d{2,4}[-−]\d{3,4}"), "[電話番号]"),
    # .co.jp 形式のサブドメインを含むメールアドレスに対応
    (re.compile(r"[\w.+-]+@[\w-]+\.(?:[a-zA-Z]{2,}\.)*[a-zA-Z]{2,}"), "[メール]"),
    (re.compile(r"\d{3}[-−]\d{4}"), "[郵便番号]"),
    (re.compile(r"(?<!\d)\d{12}(?!\d)"), "[識別番号]"),
    # 全角文字・日本語句読点・全角括弧を含まない範囲でURLを捕捉
    (re.compile(r"https?://[^\s\u3000-\u9fff\uff00-\uffef]+"), "[URL]"),
    # 都道府県名 + 市区町村 + 番地（建物名が続く場合も捕捉）
    (re.compile(
        r"(?:北海道|東京都|大阪府|京都府|\S{2,3}[都道府県])"
        r"\S+[市区町村]\S*"
        r"\d+[-−]\d+(?:[-−]\d+)?"
        r"(?:[ \u3000]\S+\d+)?"
    ), "[住所]"),
]


def apply_regex(text: str, excluded_tags: set[str] | None = None) -> tuple[str, list[dict]]:
    excluded = excluded_tags or set()
    replacements: list[dict] = []
    result = text
    for pattern, tag in _PATTERNS:
        if tag in excluded:
            continue
        for m in pattern.finditer(result):
            replacements.append({"original": m.group(), "tag": tag})
        result = pattern.sub(tag, result)
    return result, replacements
