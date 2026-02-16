FROM python:3.13-slim

ENV TZ=Asia/Tokyo
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# 依存関係のみ先にインストール（キャッシュ効率化）
COPY pyproject.toml .
RUN pip install --no-cache-dir $(python -c "import tomllib,pathlib;print(' '.join(tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['dependencies']))")

# ソースコードをコピー
COPY src/ src/

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
