import json
import logging
import requests

logger = logging.getLogger(__name__)

MASKER_SYSTEM = """\
あなたは日本語文書の個人情報マスキング専門AIです。
以下の情報を検出し対応するタグに置換してください。

置換対象:
- 人名（姓名・フルネーム・名前単体） → [氏名]
- 住所（都道府県〜番地・号室）       → [住所]
- 会社名・組織名（固有名詞）         → [会社名]
- 社員番号・顧客番号                 → [識別番号]
- その他個人を特定できる固有情報     → [個人情報]

ルール:
- すでに[タグ]形式の箇所は変更しない
- 一般的な地名・公的機関名（東京都・国税庁等）は対象外
- テキストの意味・構造を壊さない

必ず以下のJSONのみ出力（前置き・説明不要）:
{"masked_text": "...", "replacements": [{"original": "...", "tag": "..."}]}
"""

REVIEWER_SYSTEM = """\
あなたは個人情報マスキングの品質レビュアーAIです。
マスク済みテキストを受け取り、見落とされた個人情報を追加マスクします。

確認ポイント:
- 残存している人名（日本語・英語）
- 住所の断片（丁目・番地・マンション名）
- 会社名・ブランド名

ルール:
- すでに[タグ]形式の箇所はそのまま保持
- 過検出（一般名詞・地名等）は避ける
- 変更がない場合も final_text に入力テキストをそのまま返す

必ず以下のJSONのみ出力:
{"final_text": "...", "additional": [{"original": "...", "tag": "..."}], "confidence": 0.0}
"""


def _call_lm_studio(system: str, user: str, url: str, model: str, timeout: int = 120) -> dict | None:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
    }
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        start, end = clean.find("{"), clean.rfind("}") + 1
        return json.loads(clean[start:end])
    except requests.exceptions.ConnectionError as e:
        logger.error("LM Studio connection failed (%s): %s", url, e)
        return None
    except requests.exceptions.HTTPError as e:
        logger.error("LM Studio HTTP error (model=%s): %s – %s", model, e, getattr(e.response, "text", ""))
        return None
    except Exception as e:
        logger.error("LM Studio call failed: %s", e)
        return None


def call_masker(text: str, model: str, url: str) -> dict | None:
    return _call_lm_studio(MASKER_SYSTEM, text, url, model)


def call_reviewer(masked_text: str, model: str, url: str) -> dict | None:
    return _call_lm_studio(REVIEWER_SYSTEM, masked_text, url, model)
