"""GiNZA (Layer 2) と openai/privacy-filter の日本語 PII 検出比較ベンチ。

openai/privacy-filter は transformers>=4.48 を要求するが、同バージョンは
ja_ginza_electra (spacy-transformers 経由) と API 非互換のため、両者を同一
プロセスで同時に動かせない。よって `--only {ginza,pf}` で片方ずつ実行し、
各回の JSON 結果を `bench/results/` に保存、両方揃ったらマージ集計する。

実行方法:
    # GiNZA（既存 image で動作）
    python -m bench.compare_privacy_filter --only ginza

    # privacy-filter（transformers を upgrade した環境で）
    pip install --upgrade 'transformers>=4.48' torch
    python -m bench.compare_privacy_filter --only pf

    # 両方揃ったら集計
    python -m bench.compare_privacy_filter --report
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

# openai/privacy-filter のラベル → 本プロジェクトのタグ
PF_LABEL_TAG: dict[str, str] = {
    "private_person": "[氏名]",
    "private_address": "[住所]",
    "private_email": "[メール]",
    "private_phone": "[電話番号]",
    "private_url": "[URL]",
    "account_number": "[識別番号]",
    "private_date": "[日付]",  # 本プロジェクトに対応タグなし(参考表示)
    "secret": "[シークレット]",  # 同上
}


@dataclass
class Sample:
    text: str
    expected: dict[str, int]  # タグ → 期待件数


SAMPLES: list[Sample] = [
    Sample(
        "山田太郎さんの連絡先は yamada.taro@example.com、電話 090-1234-5678 です。",
        {"[氏名]": 1, "[メール]": 1, "[電話番号]": 1},
    ),
    Sample(
        "株式会社テストの田中花子（東京都渋谷区神宮前1-2-3）からご連絡いただきました。",
        {"[氏名]": 1, "[住所]": 1, "[会社名]": 1},
    ),
    Sample(
        "2025年4月1日付で、佐藤一郎は新宿区西新宿2-8-1 に転居しました。",
        {"[氏名]": 1, "[住所]": 1},
    ),
    Sample(
        "お問い合わせは https://example.co.jp/contact まで。担当: 鈴木。",
        {"[URL]": 1, "[氏名]": 1},
    ),
    Sample(
        "口座番号 1234567 への振込を高橋部長に依頼済みです。",
        {"[識別番号]": 1, "[氏名]": 1},
    ),
]


def run_ginza(text: str) -> list[tuple[str, str]]:
    """GiNZA で (original, tag) のリストを返す。"""
    from core.layer2_ner import apply_ner

    _, reps = apply_ner(text)
    return [(r["original"], r["tag"]) for r in reps]


def run_privacy_filter(text: str, pipe) -> list[tuple[str, str]]:
    """openai/privacy-filter のエンティティ → (original, tag) のリストを返す。"""
    results = pipe(text, aggregation_strategy="simple")
    out: list[tuple[str, str]] = []
    for r in results:
        label = r.get("entity_group") or r.get("entity")
        tag = PF_LABEL_TAG.get(label, f"[{label}]")
        out.append((r["word"], tag))
    return out


def count_tags(entries: list[tuple[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for _, tag in entries:
        counts[tag] = counts.get(tag, 0) + 1
    return counts


def fmt_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "(なし)"
    return ", ".join(f"{tag}×{n}" for tag, n in sorted(counts.items()))


def run_only_ginza() -> list[list[tuple[str, str]]]:
    out = []
    for s in SAMPLES:
        ents = run_ginza(s.text)
        print(f"[ginza] {s.text}\n  -> {ents}")
        out.append(ents)
    return out


def run_only_pf() -> list[list[tuple[str, str]]]:
    from transformers import pipeline

    print("=== openai/privacy-filter をロード中 ===")
    pipe = pipeline(task="token-classification", model="openai/privacy-filter")
    out = []
    for s in SAMPLES:
        ents = run_privacy_filter(s.text, pipe)
        print(f"[pf] {s.text}\n  -> {ents}")
        out.append(ents)
    return out


def save(name: str, entries: list[list[tuple[str, str]]]) -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{name}.json"
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2))
    print(f"\n保存: {path}")


def load(name: str) -> list[list[tuple[str, str]]] | None:
    path = RESULTS_DIR / f"{name}.json"
    if not path.exists():
        return None
    return [[(w, t) for w, t in row] for row in json.loads(path.read_text())]


def report() -> int:
    g = load("ginza")
    p = load("pf")
    if g is None or p is None:
        print("両方の結果が揃っていません。--only ginza / --only pf を先に実行してください。", file=sys.stderr)
        return 1

    totals = {"ginza": {"tp": 0, "fp": 0, "fn": 0}, "pf": {"tp": 0, "fp": 0, "fn": 0}}
    for i, s in enumerate(SAMPLES):
        print(f"\n--- Sample {i + 1} ---")
        print(f"入力: {s.text}")
        print(f"期待: {fmt_counts(s.expected)}")
        g_counts = count_tags(g[i])
        p_counts = count_tags(p[i])
        print(f"GiNZA          : {fmt_counts(g_counts)}   detail={g[i]}")
        print(f"privacy-filter : {fmt_counts(p_counts)}   detail={p[i]}")

        for name, cnts in (("ginza", g_counts), ("pf", p_counts)):
            for tag, want in s.expected.items():
                got = cnts.get(tag, 0)
                totals[name]["tp"] += min(got, want)
                totals[name]["fn"] += max(0, want - got)
            for tag, got in cnts.items():
                want = s.expected.get(tag, 0)
                totals[name]["fp"] += max(0, got - want)

    print("\n=== 集計（期待タグに対する TP / FP / FN） ===")
    for name in ("ginza", "pf"):
        t = totals[name]
        print(f"{name:15s}: TP={t['tp']}  FP={t['fp']}  FN={t['fn']}")
    print("\n注意: privacy-filter には [会社名] カテゴリがないため、組織名は FN 想定。")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["ginza", "pf"])
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()

    if args.report:
        return report()
    if args.only == "ginza":
        save("ginza", run_only_ginza())
        return 0
    if args.only == "pf":
        save("pf", run_only_pf())
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
