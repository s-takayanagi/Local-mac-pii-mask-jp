import re

# (pattern, tag)
_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"0[789]0[-−]\d{4}[-−]\d{4}"), "[電話番号]"),
    (re.compile(r"0\d{1,4}[-−]\d{2,4}[-−]\d{3,4}"), "[電話番号]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}"), "[メール]"),
    (re.compile(r"\d{3}[-−]\d{4}"), "[郵便番号]"),
    (re.compile(r"\d{4}年\s*\d{1,2}月\s*\d{1,2}日"), "[生年月日]"),
    (re.compile(r"(?<!\d)\d{12}(?!\d)"), "[識別番号]"),
    (re.compile(r"https?://\S+"), "[URL]"),
]


def apply_regex(text: str) -> tuple[str, list[dict]]:
    replacements: list[dict] = []
    result = text
    for pattern, tag in _PATTERNS:
        for m in pattern.finditer(result):
            replacements.append({"original": m.group(), "tag": tag})
        result = pattern.sub(tag, result)
    return result, replacements
