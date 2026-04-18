import logging
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

    def emit(self, record: logging.LogRecord) -> None:
        try:
            import streamlit as st
            if self.SESSION_KEY not in st.session_state:
                st.session_state[self.SESSION_KEY] = []
            st.session_state[self.SESSION_KEY].append(self.format(record))

            container = st.session_state.get(self.CONTAINER_KEY)
            if container is not None:
                logs = st.session_state[self.SESSION_KEY]
                visible = logs[-200:]
                with container:
                    st.code("\n".join(visible), language=None)
        except Exception:
            pass


def install(root_loggers: list[str] | None = None) -> SessionStateLogHandler:
    """Attach the handler to the given logger names (default: root + app loggers)."""
    import streamlit as st
    st.session_state[SessionStateLogHandler.SESSION_KEY] = []

    handler = SessionStateLogHandler()

    targets = root_loggers or ["", "core", "file_handlers", "ui"]
    for name in targets:
        logging.getLogger(name).addHandler(handler)

    return handler


def uninstall(handler: SessionStateLogHandler, root_loggers: list[str] | None = None) -> None:
    targets = root_loggers or ["", "core", "file_handlers", "ui"]
    for name in targets:
        logging.getLogger(name).removeHandler(handler)
