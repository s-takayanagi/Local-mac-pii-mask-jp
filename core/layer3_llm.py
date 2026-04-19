import json
import logging
import re
import time
import requests

try:
    from config import LOG_PII_IN_DEBUG
except Exception:
    LOG_PII_IN_DEBUG = False

logger = logging.getLogger(__name__)

MASKER_SYSTEM = """\
あなたは日本語文書の個人情報マスキング専門AIです。
以下の情報を検出し対応するタグに置換してください。

置換対象:
- 人名（姓名・フルネーム・名前単体） → [氏名]
- 住所（都道府県〜番地・号室）       → [住所]
- 会社名・組織名（固有名詞）         → [会社名]
- 社員番号・顧客番号                 → [識別番号]
- 電話番号（前段で見逃された場合）   → [電話番号]
- メールアドレス（同上）             → [メール]
- 郵便番号（同上）                   → [郵便番号]
- URL（同上）                         → [URL]
- その他個人を特定できる固有情報     → [個人情報]

ルール:
- すでに[タグ]形式の箇所は変更しない
- 一般的な地名・公的機関名（東京都・国税庁等）は対象外
- 部署名・部門名（〜部・〜課・〜室・〜チーム・〜グループ・〜本部・〜センター等）は[会社名]ではない。対象外とする
- 役割・担当記述（〜担当・〜責任者・東日本担当等）は個人情報ではない。対象外とする
- テキストの意味・構造を壊さない
- 以下の「属性ラベル」はマスクしない（列見出し・項目名であり、値ではない）:
  氏名 / ふりがな / フリガナ / 住所 / 電話番号 / メール / メールアドレス /
  郵便番号 / 会社名 / 組織名 / 部署 / 役職 / 顧客ID / 顧客名 / 社員番号 /
  マイナンバー / 法人番号 / 生年月日 / 年齢 / 性別 / 訪問日 / 契約日 /
  備考 / 担当者名 / 担当 など
  → 値が伴う場合のみマスク対象（例: 「顧客名: 田中」の「田中」はマスク、「顧客名」自体は対象外）

必ず以下のJSONのみ出力（前置き・説明不要）:
{"masked_text": "...", "replacements": [{"original": "...", "tag": "..."}]}
"""

REVIEWER_SYSTEM = """\
あなたは個人情報マスキングの品質レビュアーAIです。
「原文」と「マスク済みテキスト」を受け取り、以下の2点を確認します。

入力フォーマット:
入力は必ず【原文】と【マスク済みテキスト】の2セクションで渡されます。
前段でマスクが発生しなかった場合は両者が同一になることがありますが、その場合も
フォーマットは変わりません。

確認ポイント:
1. マスク済みテキストに残存している人名（日本語・英語）・住所の断片・会社名
2. 原文と比較して過検出されたマスク（一般名詞・部署名・役割記述・法律上の甲乙等）を元に戻す

ルール:
- すでに[タグ]形式の箇所はそのまま保持（過検出でない限り）
- 過検出（一般名詞・地名・部署名・役割記述・甲乙等の法律用語）は final_text で元の語に戻す
- 部署名（〜部・〜課・〜室・〜チーム・〜グループ等）を[会社名]にマスクしていたら元に戻す
- 役割・担当記述（〜担当・東日本担当等）をマスクしていたら元に戻す
- 変更がない場合も final_text にマスク済みテキストをそのまま返す

必ず以下のJSONのみ出力（前置き・説明不要）:
{"final_text": "...", "additional": [{"original": "...", "tag": "..."}], "confidence": 0.0}
"""

# LFM2-350M-PII-Extract-JP 用システムプロンプト（アルファベット順が必須）
LFM2_SYSTEM = "Extract <address>, <company_name>, <email_address>, <human_name>, <phone_number>"

# LFM2-350M-PII-Extract-JP の固有出力キーとタグのマッピング
_LFM2_TAG_MAP: dict[str, str] = {
    "address": "[住所]",
    "company_name": "[会社名]",
    "email_address": "[メール]",
    "human_name": "[氏名]",
    "phone_number": "[電話番号]",
}

# 汎用 LLM が返す replacements/additional のうち、ここに含まれるタグのみ許可する。
# 汎用モデル（qwen 等）は括弧抜けタグ・他言語ラベル・メタコメント等を返すことがあるため、
# ホワイトリスト外の出力は破棄し masked_text からも元の文字列に戻す。
_VALID_TAGS: frozenset[str] = frozenset({
    "[氏名]", "[住所]", "[会社名]", "[電話番号]",
    "[メール]", "[郵便番号]", "[URL]", "[識別番号]", "[個人情報]",
})

# 列見出し・属性ラベル（値ではない）。AI がこれら単独の語をマスク対象にしたら破棄する。
_LABEL_BLOCKLIST: frozenset[str] = frozenset({
    "氏名", "ふりがな", "フリガナ", "住所", "電話番号", "メール",
    "メールアドレス", "郵便番号", "会社名", "組織名", "部署", "部門",
    "役職", "顧客id", "顧客名", "社員番号", "社員id", "マイナンバー",
    "法人番号", "生年月日", "年齢", "性別", "訪問日", "契約日",
    "備考", "担当者名", "担当", "項目", "内容", "番号", "名前",
})


_DEPT_SUFFIX_RE = re.compile(
    r"(?:部|課|室|係|局|本部|センター|チーム|グループ|ユニット|部門|事業部|統括部)$"
)
_ROLE_SUFFIX_RE = re.compile(r"担当|責任者|リーダー|マネージャー|ディレクター")


def _is_label_only(original: str) -> bool:
    """original が属性ラベル・部署名・役割記述のみで構成されるか判定する"""
    if not original:
        return False
    normalized = re.sub(r"[（）()\s]+", "", original).lower()
    if normalized in _LABEL_BLOCKLIST:
        return True
    parts = [p.strip().lower() for p in re.split(r"[（）()・/／]+", original) if p.strip()]
    if parts and all(p in _LABEL_BLOCKLIST for p in parts):
        return True
    # 部署名パターン（〜部・〜課・〜室・〜チーム等）
    stripped = re.sub(r"[（）()\s]", "", original)
    if _DEPT_SUFFIX_RE.search(stripped):
        return True
    # 役割・担当記述（東日本担当・西日本責任者等）
    if _ROLE_SUFFIX_RE.search(original):
        return True
    return False


def _sanitize_replacements(
    text: str,
    replacements: list[dict],
    reference_text: str | None = None,
) -> tuple[str, list[dict]]:
    """汎用 LLM 出力から不正タグ・既マスク済み original を除外する。

    除外対象:
    - tag が _VALID_TAGS に含まれない（"氏名"・"公司名"・"overmasked" 等のノイズ）
    - original が既に [タグ] 形式（モデルが括弧を剥がしただけの再処理ノイズ）

    不正タグは text 内の [タグ] を元の original に戻してから破棄する。
    """
    valid: list[dict] = []
    invalid_by_tag: dict[str, list[str]] = {}

    for r in replacements:
        if not isinstance(r, dict):
            continue
        tag = r.get("tag", "")
        original = r.get("original", "")
        if not isinstance(tag, str) or not isinstance(original, str):
            continue
        if not tag or not original:
            continue
        if original.startswith("[") and original.endswith("]") and len(original) > 2:
            continue
        if tag not in _VALID_TAGS:
            invalid_by_tag.setdefault(tag, []).append(original)
            continue
        if _is_label_only(original):
            # 属性ラベル（顧客ID・訪問日等）を値として扱った誤検知。破棄して元に戻す。
            invalid_by_tag.setdefault(tag, []).append(original)
            continue
        valid.append(r)

    if not invalid_by_tag:
        return text, valid

    dropped = sum(len(v) for v in invalid_by_tag.values())
    logger.info(
        "[LM Studio] ホワイトリスト検証で %d 件の不正タグを破棄 | tags=%s",
        dropped, sorted(invalid_by_tag.keys()),
    )

    if reference_text:
        for tag, originals in invalid_by_tag.items():
            originals.sort(
                key=lambda o: reference_text.find(o) if o in reference_text else len(reference_text)
            )

    reverted = text
    for tag, originals in invalid_by_tag.items():
        for original in originals:
            if tag in reverted:
                reverted = reverted.replace(tag, original, 1)
    return reverted, valid


def _is_lfm2_model(model: str) -> bool:
    return "lfm2" in model.lower()


def _apply_lfm2_entities(
    text: str, raw: dict, excluded_tags: set[str]
) -> tuple[str, list[dict]]:
    """LFM2 形式 {"human_name": [...], ...} をテキストに適用して replacements を返す。

    位置追跡方式: 全エンティティのマッチ位置を列挙してから、
    重複するスパンを除外し、末尾から順に置換する。
    これにより「田中」が「田中太郎」の一部や既存の[氏名]タグの一部と誤って重なることを防ぐ。
    """
    pending: list[tuple[str, str]] = []
    for key, tag in _LFM2_TAG_MAP.items():
        if tag in excluded_tags:
            continue
        entities = raw.get(key, [])
        if not isinstance(entities, list):
            continue
        for entity in entities:
            if isinstance(entity, str) and entity:
                pending.append((entity, tag))

    # 長いエンティティを優先してスパン登録することで、短い部分文字列が
    # 長いエンティティ内部を奪うのを防ぐ。
    pending.sort(key=lambda x: len(x[0]), reverse=True)

    spans: list[tuple[int, int, str, str]] = []  # (start, end, entity, tag)
    occupied: list[tuple[int, int]] = []

    def _overlaps(s: int, e: int) -> bool:
        return any(not (e <= os_ or s >= oe) for os_, oe in occupied)

    for entity, tag in pending:
        start = 0
        ent_len = len(entity)
        while True:
            idx = text.find(entity, start)
            if idx == -1:
                break
            end = idx + ent_len
            if not _overlaps(idx, end):
                spans.append((idx, end, entity, tag))
                occupied.append((idx, end))
            start = end

    spans.sort(key=lambda x: x[0], reverse=True)
    masked = text
    replacements: list[dict] = []
    for s, e, entity, tag in spans:
        masked = masked[:s] + tag + masked[e:]
        replacements.append({"original": entity, "tag": tag})
    # 出現順（左→右）に並べ直して返す
    replacements.reverse()
    return masked, replacements


def _call_lm_studio(
    system: str, user: str, url: str, model: str, role: str,
    timeout: int = 120, temperature: float = 0.05,
) -> dict | None:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": 4096,
    }

    prompt_chars = len(system) + len(user)
    logger.info(
        "[LM Studio] %s リクエスト | model=%s | url=%s | プロンプト文字数=%d",
        role, model, url, prompt_chars,
    )
    # 入力テキストはマスク前の原文（PII）を含みうるため、明示的にフラグが立った場合のみ出力する。
    if LOG_PII_IN_DEBUG:
        logger.debug("[LM Studio] %s 入力テキスト:\n%s", role, user)

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
        # 生レスポンスはマスク後テキストだが LLM が原文を復唱する可能性があるため、同じ PII ガードを適用する。
        if LOG_PII_IN_DEBUG:
            logger.debug("[LM Studio] %s 生レスポンス:\n%s", role, raw)

        clean = raw.strip().removeprefix("```json").removesuffix("```").strip()
        start_idx = clean.find("{")
        if start_idx == -1:
            logger.error(
                "[LM Studio] %s JSON境界検出失敗 | raw先頭200文字: %s",
                role, raw[:200],
            )
            return None
        # raw_decode は start_idx から一つの有効な JSON オブジェクトを厳密に切り出すため、
        # rfind("}") に頼る方式より終端位置が明確で、複数の "}" を含むテキストでも安全。
        try:
            result, _end = json.JSONDecoder().raw_decode(clean, start_idx)
        except json.JSONDecodeError as e:
            logger.error("[LM Studio] %s JSONパースエラー | %s | raw先頭200文字: %s",
                         role, e, raw[:200])
            return None

        # 標準スキーマ (Masker: replacements / Reviewer: additional) と
        # LFM2 スキーマ（human_name / address 等の配列）の両方に対応してログ件数を算出
        if isinstance(result.get("replacements"), list):
            rep_count = len(result["replacements"])
        elif isinstance(result.get("additional"), list):
            rep_count = len(result["additional"])
        else:
            rep_count = sum(
                len(v) for k, v in result.items()
                if k in _LFM2_TAG_MAP and isinstance(v, list)
            )
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


def _revert_excluded(
    text: str,
    replacements: list[dict],
    excluded_tags: set[str],
    reference_text: str | None = None,
) -> tuple[str, list[dict]]:
    """excluded_tags に該当する置換を text 内で元の文字列に戻す。

    同じタグが複数回現れる場合、replacements の順序に依存すると誤対応になるため、
    reference_text（マスク前テキスト）が渡されたときは original の出現位置順で
    ソートし、text 内の [タグ] を左から順に対応する original に置換する。
    """
    kept: list[dict] = []
    to_revert_by_tag: dict[str, list[str]] = {}
    for r in replacements:
        tag = r.get("tag", "")
        original = r.get("original", "")
        if tag in excluded_tags and original and tag:
            to_revert_by_tag.setdefault(tag, []).append(original)
        else:
            kept.append(r)

    if reference_text:
        for tag, originals in to_revert_by_tag.items():
            originals.sort(
                key=lambda o: reference_text.find(o) if o in reference_text else len(reference_text)
            )

    reverted = text
    for tag, originals in to_revert_by_tag.items():
        for original in originals:
            if tag in reverted:
                reverted = reverted.replace(tag, original, 1)
    return reverted, kept


def call_masker(text: str, model: str, url: str, excluded_tags: set[str] | None = None) -> dict | None:
    excluded = excluded_tags or set()

    if _is_lfm2_model(model):
        logger.debug("[Layer3 Masker] LFM2 モード: 専用システムプロンプト / temperature=0")
        raw = _call_lm_studio(LFM2_SYSTEM, text, url, model, role="Layer3 Masker", temperature=0)
        if raw is None:
            return None
        masked, reps = _apply_lfm2_entities(text, raw, excluded)
        return {"masked_text": masked, "replacements": reps}

    result = _call_lm_studio(MASKER_SYSTEM, text, url, model, role="Layer3 Masker")
    if result is None:
        return result
    reps = result.get("replacements", [])
    if not isinstance(reps, list):
        reps = []
    masked = result.get("masked_text", text)
    if not isinstance(masked, str) or not masked:
        masked = text
    masked, reps = _sanitize_replacements(masked, reps, reference_text=text)
    if excluded_tags:
        masked, reps = _revert_excluded(masked, reps, excluded_tags, reference_text=text)
    result["masked_text"] = masked
    result["replacements"] = reps
    return result


def call_reviewer(
    masked_text: str,
    model: str,
    url: str,
    excluded_tags: set[str] | None = None,
    original_text: str | None = None,
) -> dict | None:
    excluded = excluded_tags or set()

    if _is_lfm2_model(model):
        logger.debug("[Layer4 Reviewer] LFM2 モード: 専用システムプロンプト / temperature=0")
        raw = _call_lm_studio(LFM2_SYSTEM, masked_text, url, model, role="Layer4 Reviewer", temperature=0)
        if raw is None:
            return None
        final, additional = _apply_lfm2_entities(masked_text, raw, excluded)
        return {"final_text": final, "additional": additional, "confidence": 0.95}

    # プロンプト側の入力フォーマットと揃えるため、original_text が無くても
    # 常に【原文】/【マスク済みテキスト】の2セクション形式で送る
    source = original_text if original_text is not None else masked_text
    user_message = f"【原文】\n{source}\n\n【マスク済みテキスト】\n{masked_text}"

    result = _call_lm_studio(REVIEWER_SYSTEM, user_message, url, model, role="Layer4 Reviewer")
    if result is None:
        return result
    additional = result.get("additional", [])
    if not isinstance(additional, list):
        additional = []
    final = result.get("final_text", masked_text)
    if not isinstance(final, str) or not final:
        final = masked_text
    # Reviewer は masked_text を読んで追加検出するため、位置参照は masked_text を使う
    final, additional = _sanitize_replacements(final, additional, reference_text=masked_text)
    if excluded_tags:
        final, additional = _revert_excluded(final, additional, excluded_tags, reference_text=masked_text)
    result["final_text"] = final
    result["additional"] = additional
    return result
