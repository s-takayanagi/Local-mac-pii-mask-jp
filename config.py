import os

# Docker内からMacホストのLM Studioへ接続するため host.docker.internal を使う
# ローカル直接実行時は LM_STUDIO_HOST=localhost を環境変数で上書き可能
_host = os.environ.get("LM_STUDIO_HOST", "host.docker.internal")
_port = os.environ.get("LM_STUDIO_PORT", "1234")

LM_STUDIO_URL = f"http://{_host}:{_port}/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("LM_STUDIO_MODEL", "qwen/qwen3.5-9b")
OUTPUT_SUFFIX = "_masked"
SUPPORTED_EXTENSIONS = [".xlsx", ".pptx", ".docx"]
REQUEST_TIMEOUT = 120

# ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）。
# 本番運用では INFO 以上を推奨。DEBUG にすると詳細な内部状態が出力される。
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# LM Studio 入出力テキスト（= マスク前の原文を含みうる）を DEBUG ログに出力するか。
# 既定は False。デバッグ時のみ LOG_PII_IN_DEBUG=true を明示指定する。
LOG_PII_IN_DEBUG = os.environ.get("LOG_PII_IN_DEBUG", "false").lower() in ("true", "1", "yes")
