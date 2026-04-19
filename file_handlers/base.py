import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Protocol
from models import ProcessResult


class FileHandler(Protocol):
    def __call__(self, path: Path, model: str, lm_studio_url: str) -> ProcessResult:
        ...


def masked_output_path(path: Path, suffix: str = "_masked") -> Path:
    return path.with_stem(path.stem + suffix)


def _attach_streamlit_ctx_initializer():
    """ThreadPoolExecutor の initializer 用。Streamlit 実行中なら現在の
    ScriptRunContext を取得し、ワーカースレッドに引き継ぐクロージャを返す。

    Streamlit 配下でない場合や import に失敗した場合は no-op initializer を返す。
    これにより file_handlers は Streamlit への直接依存を持たず、CLI/テスト実行でも
    そのまま動作する。
    """
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx, add_script_run_ctx
    except Exception:
        return lambda: None

    ctx = get_script_run_ctx()
    if ctx is None:
        return lambda: None

    def _init():
        try:
            add_script_run_ctx(threading.current_thread(), ctx)
        except Exception:
            pass

    return _init


def mask_texts(
    texts: list[str],
    model: str,
    lm_studio_url: str,
    enabled_layers,
    excluded_tags,
    max_workers: int,
):
    """mask_text を serial / parallel のいずれかで呼び出す共通ヘルパ。

    parallel 実行時は Streamlit の ScriptRunContext をワーカースレッドに伝播し、
    ログハンドラから st.session_state へのアクセスが失敗しないようにする。
    """
    from core.pipeline import mask_text

    if max_workers <= 1 or len(texts) <= 1:
        return [mask_text(t, model, lm_studio_url, enabled_layers, excluded_tags) for t in texts]

    initializer = _attach_streamlit_ctx_initializer()
    with ThreadPoolExecutor(max_workers=max_workers, initializer=initializer) as ex:
        return list(ex.map(
            lambda t: mask_text(t, model, lm_studio_url, enabled_layers, excluded_tags),
            texts,
        ))
