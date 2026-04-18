import json
import logging
import time
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


def _call_lm_studio(
    system: str, user: str, url: str, model: str, role: str, timeout: int = 120
) -> dict | None:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.05,
        "max_tokens": 4096,
    }

    prompt_chars = len(system) + len(user)
    logger.info(
        "[LM Studio] %s リクエスト | model=%s | url=%s | プロンプト文字数=%d",
        role, model, url, prompt_chars,
    )

    start = time.monotonic()
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.monotonic() - start

        logger.info(
            "[LM Studio] %s レスポンス | HTTP %d | 経過時間=%.2fs",
            role, resp.status_code, elapsed,
        )

        resp.raise_for_status()
        raw_json = resp.json()

        usage = raw_json.get("usage", {})
        if usage:
            logger.info(
                "[LM Studio] %s トークン使用量 | prompt=%s | completion=%s | total=%s",
                role,
                usage.get("prompt_tokens", "?"),
                usage.get("completion_tokens", "?"),
                usage.get("total_tokens", "?"),
            )

        raw = raw_json["choices"][0]["message"]["content"]
        logger.debug("[LM Studio] %s 生レスポンス | %s", role, raw[:300])

        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        start_idx, end_idx = clean.find("{"), clean.rfind("}") + 1
        result = json.loads(clean[start_idx:end_idx])

        rep_count = len(result.get("replacements", result.get("additional", [])))
        logger.info("[LM Studio] %s パース完了 | 検出件数=%d", role, rep_count)

        return result

    except requests.exceptions.ConnectionError as e:
        elapsed = time.monotonic() - start
        logger.error(
            "[LM Studio] %s 接続エラー (%.2fs) | url=%s | %s", role, elapsed, url, e
        )
        return None
    except requests.exceptions.Timeout:
        elapsed = time.monotonic() - start
        logger.error(
            "[LM Studio] %s タイムアウト (%.2fs) | timeout=%ds", role, elapsed, timeout
        )
        return None
    except requests.exceptions.HTTPError as e:
        elapsed = time.monotonic() - start
        logger.error(
            "[LM Studio] %s HTTPエラー (%.2fs) | model=%s | %s | body=%s",
            role, elapsed, model, e, getattr(e.response, "text", "")[:200],
        )
        return None
    except json.JSONDecodeError as e:
        logger.error("[LM Studio] %s JSONパースエラー | %s", role, e)
        return None
    except Exception as e:
        logger.error("[LM Studio] %s 予期しないエラー | %s", role, e)
        return None


def call_masker(text: str, model: str, url: str) -> dict | None:
    return _call_lm_studio(MASKER_SYSTEM, text, url, model, role="Layer3 Masker")


def call_reviewer(masked_text: str, model: str, url: str) -> dict | None:
    return _call_lm_studio(REVIEWER_SYSTEM, masked_text, url, model, role="Layer4 Reviewer")
