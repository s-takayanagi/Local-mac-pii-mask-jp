import streamlit as st
import requests
from pathlib import Path

from config import LM_STUDIO_URL, DEFAULT_MODEL, SUPPORTED_EXTENSIONS, OUTPUT_SUFFIX
from file_handlers.xlsx_handler import process_xlsx
from file_handlers.pptx_handler import process_pptx
from file_handlers.docx_handler import process_docx

_HANDLERS = {".xlsx": process_xlsx, ".pptx": process_pptx, ".docx": process_docx}


def check_lm_studio_connection(url: str = LM_STUDIO_URL) -> dict:
    base = url.rsplit("/chat", 1)[0]
    try:
        resp = requests.get(f"{base}/models", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        models = [m["id"] for m in data.get("data", [])]
        return {"ok": True, "models": models or [DEFAULT_MODEL]}
    except Exception:
        return {"ok": False, "models": [DEFAULT_MODEL]}


def run_masking(folder: str, model: str, suffix: str):
    folder_path = Path(folder)
    files = [
        f for f in folder_path.iterdir()
        if f.suffix.lower() in SUPPORTED_EXTENSIONS and not f.name.startswith("~$")
    ]
    if not files:
        st.warning("対象ファイルが見つかりませんでした")
        return

    progress = st.progress(0)
    log = st.empty()
    results = []

    for i, f in enumerate(files):
        log.text(f"処理中: {f.name}")
        try:
            result = _HANDLERS[f.suffix.lower()](f, model, LM_STUDIO_URL)
            results.append((f.name, result.output_path.name, result.total_replacements, None))
        except Exception as e:
            results.append((f.name, None, 0, str(e)))
        progress.progress((i + 1) / len(files))

    log.empty()
    st.session_state["results"] = results
    st.session_state["done"] = True


def main():
    st.set_page_config(page_title="PII Masker", layout="wide")
    st.title("PII Masker")

    with st.sidebar:
        st.header("設定")
        lm_status = check_lm_studio_connection()
        if lm_status["ok"]:
            st.success("LM Studio: 接続中")
        else:
            st.error("LM Studio: 未接続")
            st.caption("LM Studio を起動してモデルをロードしてください")

        selected_model = st.selectbox("モデル", lm_status["models"])
        suffix = st.text_input("出力サフィックス", value=OUTPUT_SUFFIX)

    folder = st.text_input("処理フォルダのパスを入力してください")

    if st.button("マスキング開始", disabled=not folder or not lm_status["ok"]):
        st.session_state["done"] = False
        run_masking(folder, selected_model, suffix)

    if st.session_state.get("done"):
        results = st.session_state.get("results", [])
        total = sum(r[2] for r in results)
        st.success(f"完了: {len(results)} ファイル / {total} 件置換")

        for name, out, count, err in results:
            if err:
                st.error(f"✗ {name}: {err}")
            else:
                st.text(f"✓ {name} → {out} ({count}件)")


if __name__ == "__main__":
    main()
