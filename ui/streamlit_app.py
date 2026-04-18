import logging
import streamlit as st
import requests
from pathlib import Path

from config import LM_STUDIO_URL, DEFAULT_MODEL, SUPPORTED_EXTENSIONS
from file_handlers.xlsx_handler import process_xlsx
from file_handlers.pptx_handler import process_pptx
from file_handlers.docx_handler import process_docx
from ui.log_handler import install as install_log_handler, uninstall as uninstall_log_handler

logging.basicConfig(level=logging.DEBUG)

_HANDLERS = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}

_PII_CATEGORIES = [
    ("氏名", "[氏名]"),
    ("住所", "[住所]"),
    ("電話番号", "[電話番号]"),
    ("メールアドレス", "[メール]"),
    ("会社名・組織名", "[会社名]"),
    ("郵便番号", "[郵便番号]"),
    ("生年月日", "[生年月日]"),
    ("マイナンバー等12桁", "[識別番号]"),
    ("URL", "[URL]"),
    ("その他個人情報", "[個人情報]"),
]

_LAYER_INFO = [
    ("layer1", "Layer 1", "正規表現"),
    ("layer2", "Layer 2", "固有名詞認識"),
    ("layer3", "Layer 3", "AI マスキング"),
    ("layer4", "Layer 4", "AI レビュー"),
]

_LAYER_LABELS = {
    "layer1": "Layer 1 正規表現",
    "layer2": "Layer 2 固有名詞認識",
    "layer3": "Layer 3 AI マスキング",
    "layer4": "Layer 4 AI レビュー",
}

_LOG_LEVEL_ICON = {
    "DEBUG": "🔍",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🔥",
}


def check_lm_studio_connection(url: str = LM_STUDIO_URL) -> dict:
    base = url.rsplit("/chat", 1)[0]
    try:
        resp = requests.get(f"{base}/models", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", [])]
        return {"ok": True, "models": models or [DEFAULT_MODEL], "error": None}
    except requests.exceptions.ConnectionError:
        return {
            "ok": False,
            "models": [DEFAULT_MODEL],
            "error": f"{base} に接続できません。LM Studio が起動しているか確認してください。",
        }
    except requests.exceptions.Timeout:
        return {
            "ok": False,
            "models": [DEFAULT_MODEL],
            "error": "接続タイムアウト (3秒)。LM Studio のレスポンスを確認してください。",
        }
    except Exception as e:
        return {"ok": False, "models": [DEFAULT_MODEL], "error": str(e)}


def _render_layer_summary(layer_totals: dict) -> None:
    if not layer_totals:
        st.caption("レイヤー情報なし（処理スキップまたはエラー）")
        return
    cols = st.columns(4)
    for i, (key, num, name) in enumerate(_LAYER_INFO):
        count = layer_totals.get(key)
        with cols[i]:
            if count is None:
                st.metric(label=f"{num} {name}", value="—")
            else:
                st.metric(label=f"{num} {name}", value=f"{count}件")


def _build_replacement_log_text(all_entries: list[dict]) -> str:
    if not all_entries:
        return "（置換なし）"
    lines = ["=== PII マスキングログ ===", ""]
    current_file = None
    for entry in all_entries:
        f = entry.get("file", "")
        if f != current_file:
            current_file = f
            lines.append(f"[{f}]")
        layer_label = _LAYER_LABELS.get(entry.get("layer", ""), entry.get("layer", ""))
        orig = entry.get("original", "")
        tag = entry.get("tag", "")
        loc = entry.get("location", "")
        lines.append(f'  {loc} | {layer_label} | "{orig}" → "{tag}"')
    lines.append("")
    lines.append(f"合計: {len(all_entries)} 件置換")
    return "\n".join(lines)


def _render_live_replacement_log(entries: list[dict], container) -> None:
    if not entries:
        return
    with container:
        st.markdown("#### リアルタイムログ")
        rows = [
            {
                "ファイル": e.get("file", ""),
                "場所": e.get("location", ""),
                "レイヤー": _LAYER_LABELS.get(e.get("layer", ""), e.get("layer", "")),
                "元テキスト": e.get("original", ""),
                "置換後": e.get("tag", ""),
            }
            for e in entries[-50:]
        ]
        st.dataframe(rows, use_container_width=True, hide_index=True)
        if len(entries) > 50:
            st.caption(f"最新50件を表示中（合計 {len(entries)} 件）")


def _render_system_log(container, sys_logs: list[str], max_lines: int = 200) -> None:
    with container:
        if not sys_logs:
            return
        st.markdown("#### システムログ")
        visible = sys_logs[-max_lines:]
        text = "\n".join(visible)
        st.code(text, language=None)
        if len(sys_logs) > max_lines:
            st.caption(f"最新 {max_lines} 行を表示中（合計 {len(sys_logs)} 行）")


def run_masking(folder: str, model: str, enabled_layers: set[str], excluded_tags: set[str] | None = None) -> None:
    folder_path = Path(folder)
    if not folder_path.is_dir():
        st.error(f"フォルダが見つかりません: {folder}")
        return

    files = [
        f for f in folder_path.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~$")
    ]
    if not files:
        st.warning("対象ファイルが見つかりませんでした（xlsx / pptx / docx）")
        return

    log_handler = install_log_handler()

    progress = st.progress(0.0, text="処理準備中...")
    status = st.empty()

    # 置換ログとシステムログをそれぞれ独立したコンテナで表示
    live_replacement_container = st.empty()
    st.markdown("#### システムログ")
    sys_log_container = st.empty()
    st.session_state["_log_display_container"] = sys_log_container

    results = []
    all_log_entries: list[dict] = []

    for i, f in enumerate(files):
        progress.progress(i / len(files), text=f"処理中 ({i + 1}/{len(files)}): {f.name}")
        status.info(f"⏳ **{f.name}** を処理しています…")

        logging.getLogger(__name__).info("=== ファイル処理開始: %s ===", f.name)
        try:
            result = _HANDLERS[f.suffix.lower()](f, model, LM_STUDIO_URL, enabled_layers, excluded_tags)
            file_entries = [{**r, "file": f.name} for r in result.replacements_log]
            all_log_entries.extend(file_entries)
            logging.getLogger(__name__).info(
                "=== ファイル処理完了: %s | 置換=%d件 ===", f.name, result.total_replacements
            )
            results.append({
                "name": f.name,
                "out": result.output_path.name,
                "count": result.total_replacements,
                "error": None,
                "errors": result.errors,
                "layer_totals": result.layer_totals,
                "replacements_log": result.replacements_log,
            })
        except Exception as e:
            logging.getLogger(__name__).error("ファイル処理エラー: %s | %s", f.name, e)
            results.append({
                "name": f.name,
                "out": None,
                "count": 0,
                "error": str(e),
                "errors": [],
                "layer_totals": {},
                "replacements_log": [],
            })

        # ファイルごとに置換ログを更新（システムログはemitから自動更新）
        _render_live_replacement_log(all_log_entries, live_replacement_container)

    progress.progress(1.0, text="すべてのファイルの処理が完了しました")
    status.empty()
    live_replacement_container.empty()
    st.session_state.pop("_log_display_container", None)

    uninstall_log_handler(log_handler)

    st.session_state["results"] = results
    st.session_state["all_log_entries"] = all_log_entries
    st.session_state["done"] = True


def main() -> None:
    st.set_page_config(page_title="PII Masker", layout="wide")
    st.title("PII Masker")

    with st.sidebar:
        st.header("設定")
        lm_status = check_lm_studio_connection()

        if lm_status["ok"]:
            st.success("LM Studio: 接続中")
        else:
            st.error("LM Studio: 未接続")
            if lm_status["error"]:
                st.caption(lm_status["error"])

        selected_model = st.selectbox("モデル", lm_status["models"])

        st.divider()
        st.markdown("**処理レイヤー**")
        use_layer1 = st.checkbox("1️⃣ 正規表現", value=True)
        use_layer2 = st.checkbox("2️⃣ 固有名詞認識 (NER)", value=True)
        use_layer3 = st.checkbox("3️⃣ AI マスキング (LLM)", value=True)
        use_layer4 = st.checkbox("4️⃣ AI レビュー (LLM)", value=True)

        enabled_layers: set[str] = set()
        if use_layer1:
            enabled_layers.add("layer1")
        if use_layer2:
            enabled_layers.add("layer2")
        if use_layer3:
            enabled_layers.add("layer3")
        if use_layer4:
            enabled_layers.add("layer4")

        st.divider()
        st.markdown("**除外する項目**")
        excluded_tags: set[str] = set()
        for label, tag in _PII_CATEGORIES:
            if not st.checkbox(label, value=True, key=f"pii_{tag}"):
                excluded_tags.add(tag)

    needs_lm = bool(enabled_layers & {"layer3", "layer4"})

    folder = st.text_input(
        "処理フォルダのパスを入力してください",
        placeholder="/path/to/folder",
    )

    can_start = bool(folder) and (not needs_lm or lm_status["ok"]) and bool(enabled_layers)
    if needs_lm and not lm_status["ok"]:
        st.warning("Layer 3 / Layer 4 が有効なため、LM Studio に接続できないとマスキングを開始できません。")

    if st.button("マスキング開始", disabled=not can_start):
        st.session_state["done"] = False
        st.session_state["all_log_entries"] = []
        st.session_state["system_logs"] = []
        run_masking(folder, selected_model, enabled_layers, excluded_tags)

    if st.session_state.get("done"):
        results = st.session_state.get("results", [])
        all_log_entries = st.session_state.get("all_log_entries", [])
        system_logs = st.session_state.get("system_logs", [])
        total = sum(r["count"] for r in results)
        has_errors = any(r["error"] or r["errors"] for r in results)

        if has_errors:
            st.warning(
                f"処理完了: {len(results)} ファイル / 合計 {total} 件置換（一部エラーあり）"
            )
        else:
            st.success(f"処理完了: {len(results)} ファイル / 合計 {total} 件置換")

        st.markdown("---")

        # 応答なしエラー表示フィルター
        def _is_soft_error(msg: str) -> bool:
            return "応答なし" in msg

        soft_error_count = sum(
            sum(1 for e in r["errors"] if _is_soft_error(e))
            for r in results
        )
        show_soft_errors = False
        if soft_error_count > 0:
            show_soft_errors = st.checkbox(
                f"応答なしエラーを表示する（{soft_error_count} 件・処理は継続済み）",
                value=False,
            )

        # ファイルごとの詳細
        for r in results:
            hard_errors = [e for e in r["errors"] if not _is_soft_error(e)]
            soft_errors = [e for e in r["errors"] if _is_soft_error(e)]
            visible_errors = hard_errors + (soft_errors if show_soft_errors else [])
            has_visible_issues = bool(r["error"] or visible_errors)

            icon = "✅" if not r["error"] and not r["errors"] else ("⚠️" if r["errors"] else "❌")
            header = f"{icon} {r['name']}"
            if r["out"]:
                header += f"  →  {r['out']}  （{r['count']}件）"

            with st.expander(header, expanded=has_visible_issues):
                if r["error"]:
                    st.error(f"ファイル処理エラー: {r['error']}")

                st.markdown("**レイヤー別検出件数**")
                _render_layer_summary(r["layer_totals"])

                if visible_errors:
                    st.markdown("**処理中エラー一覧**")
                    for err in visible_errors:
                        st.warning(err)
                elif soft_errors and not show_soft_errors:
                    st.caption(f"応答なしエラー {len(soft_errors)} 件（処理継続済み・上部チェックボックスで表示）")

                if r["replacements_log"]:
                    st.markdown("**置換詳細**")
                    rows = [
                        {
                            "場所": e.get("location", ""),
                            "レイヤー": _LAYER_LABELS.get(e.get("layer", ""), e.get("layer", "")),
                            "元テキスト": e.get("original", ""),
                            "置換後": e.get("tag", ""),
                        }
                        for e in r["replacements_log"]
                    ]
                    st.dataframe(rows, use_container_width=True, hide_index=True)

        # 置換ログ（コピー用）
        if all_log_entries:
            st.markdown("---")
            st.markdown("### 置換ログ（コピー用）")
            st.code(_build_replacement_log_text(all_log_entries), language=None)

        # システムログ（コピー用）
        st.markdown("---")
        with st.expander("🔧 システムログ（デバッグ用）", expanded=False):
            if system_logs:
                st.code("\n".join(system_logs), language=None)
            else:
                st.caption("ログなし")


if __name__ == "__main__":
    main()
