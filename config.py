import os

# Docker内からMacホストのLM Studioへ接続するため host.docker.internal を使う
# ローカル直接実行時は LM_STUDIO_HOST=localhost を環境変数で上書き可能
_host = os.environ.get("LM_STUDIO_HOST", "host.docker.internal")
_port = os.environ.get("LM_STUDIO_PORT", "1234")

LM_STUDIO_URL = f"http://{_host}:{_port}/v1/chat/completions"
DEFAULT_MODEL = os.environ.get("LM_STUDIO_MODEL", "qwen2.5-7b-instruct")
OUTPUT_SUFFIX = "_masked"
SUPPORTED_EXTENSIONS = [".xlsx", ".pptx", ".docx"]
REQUEST_TIMEOUT = 120
