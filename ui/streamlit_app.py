import streamlit as st
import requests
import logging
from pathlib import Path

from config import LM_STUDIO_URL, DEFAULT_MODEL, SUPPORTED_EXTENSIONS, OUTPUT_SUFFIX
from file_handlers.xlsx_handler import process_xlsx
from file_handlers.pptx_handler import process_pptx
from file_handlers.docx_handler import process_docx

logging.basicConfig(level=logging.INFO)

_HANDLERS = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}

_LAYER_INFO = [
    ("layer1", "Layer 1", "正規表現"),
    ("layer2", "Layer 2", "固有名詞認識"),
    ("layer3", "Layer 3", "AI マスキング"),
    ("layer4", "Layer 4", "AI レビュー"),
]


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


def run_masking(folder: str, model: str) -> None:
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

    progress = st.progress(0.0, text="処理準備中...")
    status = st.empty()
    results = []

    for i, f in enumerate(files):
        progress.progress(i / len(files), text=f"処理中 ({i + 1}/{len(files)}): {f.name}")
        status.info(f"⏳ **{f.name}** を処理しています…")
        try:
            result = _HANDLERS[f.suffix.lower()](f, model, LM_STUDIO_URL)
            results.append({
                "name": f.name,
                "out": result.output_path.name,
                "count": result.total_replacements,
                "error": None,
                "errors": result.errors,
                "layer_totals": result.layer_totals,
            })
        except Exception as e:
            results.append({
                "name": f.name,
                "out": None,
                "count": 0,
                "error": str(e),
                "errors": [],
                "layer_totals": {},
            })

    progress.progress(1.0, text="すべてのファイルの処理が完了しました")
    status.empty()
    st.session_state["results"] = results
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
        st.caption("処理レイヤー")
        st.caption("1️⃣ 正規表現  →  2️⃣ 固有名詞認識")
        st.caption("3️⃣ AI マスキング  →  4️⃣ AI レビュー")

    folder = st.text_input(
        "処理フォルダのパスを入力してください",
        placeholder="/path/to/folder",
    )

    can_start = bool(folder) and lm_status["ok"]
    if not lm_status["ok"]:
        st.warning("LM Studio に接続できないため、マスキングを開始できません。")

    if st.button("マスキング開始", disabled=not can_start):
        st.session_state["done"] = False
        run_masking(folder, selected_model)

    if st.session_state.get("done"):
        results = st.session_state.get("results", [])
        total = sum(r["count"] for r in results)
        has_errors = any(r["error"] or r["errors"] for r in results)

        if has_errors:
            st.warning(
                f"処理完了: {len(results)} ファイル / 合計 {total} 件置換（一部エラーあり）"
            )
        else:
            st.success(f"処理完了: {len(results)} ファイル / 合計 {total} 件置換")

        st.markdown("---")
        for r in results:
            icon = "✅" if not r["error"] and not r["errors"] else ("⚠️" if r["errors"] else "❌")
            header = f"{icon} {r['name']}"
            if r["out"]:
                header += f"  →  {r['out']}  （{r['count']}件）"

            with st.expander(header, expanded=bool(r["error"] or r["errors"])):
                if r["error"]:
                    st.error(f"ファイル処理エラー: {r['error']}")

                st.markdown("**レイヤー別検出件数**")
                _render_layer_summary(r["layer_totals"])

                if r["errors"]:
                    st.markdown("**処理中エラー一覧**")
                    for err in r["errors"]:
                        st.warning(err)


if __name__ == "__main__":
    main()
