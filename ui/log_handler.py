import logging
import threading
from datetime import datetime, timezone, timedelta

_JST = timezone(timedelta(hours=9))


class _JSTFormatter(logging.Formatter):
    def formatTime(self, record: logging.LogRecord, datefmt: str | None = None) -> str:
        ct = datetime.fromtimestamp(record.created, tz=_JST)
        return ct.strftime(datefmt or "%H:%M:%S")


class SessionStateLogHandler(logging.Handler):
    """Captures log records into st.session_state for real-time display in the UI."""

    SESSION_KEY = "system_logs"
    CONTAINER_KEY = "_log_display_container"

    def __init__(self, level: int = logging.DEBUG) -> None:
        super().__init__(level)
        fmt = "%(asctime)s JST [%(levelname)s] %(name)s: %(message)s"
        self.setFormatter(_JSTFormatter(fmt, datefmt="%H:%M:%S"))
        # 並列ワーカーから同時に emit されるケースに備えたロック。
        # append 自体は GIL で安全だが、session_state への読み書きと
        # container への再レンダリングを一つの塊として直列化する。
        self._lock = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import streamlit as st
        except Exception:
            return

        formatted = self.format(record)
        with self._lock:
            try:
                if self.SESSION_KEY not in st.session_state:
                    st.session_state[self.SESSION_KEY] = []
                st.session_state[self.SESSION_KEY].append(formatted)

                container = st.session_state.get(self.CONTAINER_KEY)
                if container is not None:
                    logs = st.session_state[self.SESSION_KEY]
                    visible = logs[-200:]
                    with container:
                        st.code("\n".join(visible), language=None)
            except Exception:
                # Streamlit コンテキスト欠落等は握りつぶす（ログ表示の失敗でアプリを止めない）
                pass


def install() -> SessionStateLogHandler:
    """Attach the handler to the root logger only (child loggers propagate up)."""
    import streamlit as st
    st.session_state[SessionStateLogHandler.SESSION_KEY] = []

    root = logging.getLogger()
    # Remove existing SessionStateLogHandler instances to avoid duplicates on re-run
    for h in root.handlers[:]:
        if isinstance(h, SessionStateLogHandler):
            root.removeHandler(h)

    handler = SessionStateLogHandler()
    root.addHandler(handler)

    return handler


def uninstall(handler: SessionStateLogHandler) -> None:
    logging.getLogger().removeHandler(handler)
