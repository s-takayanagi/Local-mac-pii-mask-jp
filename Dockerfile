FROM python:3.11-slim

WORKDIR /app

# システム依存（GiNZA/spaCy のビルドに必要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# uv をインストール
RUN pip install --no-cache-dir uv

# 依存関係を先にコピーしてキャッシュ効率を上げる
COPY pyproject.toml ./
RUN uv pip install --system --no-cache \
    streamlit \
    fastmcp \
    openpyxl \
    python-pptx \
    python-docx \
    requests \
    ginza \
    ja-ginza-electra \
    spacy

# GiNZA モデルをイメージに焼き込む（コンテナ起動後はオフライン動作）
RUN python -m spacy download ja_ginza_electra

# アプリコードをコピー
COPY . .

EXPOSE 8501

ENV LM_STUDIO_HOST=host.docker.internal
ENV LM_STUDIO_PORT=1234

ENTRYPOINT ["python", "main.py"]
CMD ["--mode", "ui"]
