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
    # \S+ は貪欲で文章内の離れた塊まで巻き込むため、空白・句読点・読点を境界にして
    # 長さも上限付きで捕捉する。
    (re.compile(
        r"(?:北海道|東京都|大阪府|京都府|\S{2,3}[都道府県])"
        r"[^\s。、,，]{1,15}?[市区町村]"
        r"[^\s。、,，]{0,20}?"
        r"\d+[-−]\d+(?:[-−]\d+)?"
        r"(?:[ \u3000]?[^\s。、,，]{1,30}\d+)?"
    ), "[住所]"),
]


def apply_regex(text: str, excluded_tags: set[str] | None = None) -> tuple[str, list[dict]]:
    """正規表現で PII をマスキングする。

    全パターンのマッチを先に原文から収集し、重複するスパンを除外してから
    末尾から順に置換する。これにより finditer 実行中に result が変化して
    位置情報がずれる問題や、後段パターンが前段で挿入したタグを巻き込む問題を防ぐ。
    """
    excluded = excluded_tags or set()
    spans: list[tuple[int, int, str, str]] = []  # (start, end, matched, tag)
    occupied: list[tuple[int, int]] = []

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= os_ or s >= oe) for os_, oe in occupied)

    for pattern, tag in _PATTERNS:
        if tag in excluded:
            continue
        for m in pattern.finditer(text):
            s, e = m.start(), m.end()
            if _overlaps(s, e):
                continue
            spans.append((s, e, m.group(), tag))
            occupied.append((s, e))

    spans.sort(key=lambda x: x[0])
    replacements: list[dict] = [
        {"original": matched, "tag": tag} for _, _, matched, tag in spans
    ]

    result = text
    for s, e, _, tag in sorted(spans, key=lambda x: x[0], reverse=True):
        result = result[:s] + tag + result[e:]
    return result, replacements
