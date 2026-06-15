FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    GRADIO_SERVER_NAME=0.0.0.0 \
    GRADIO_SERVER_PORT=7860 \
    USE_MODAL_INFERENCE=true \
    TOKEN_HOLDEM_MODAL_DEMO_MODE=true

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential curl git \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir uv

COPY . .

RUN uv pip install --system \
    "gradio>=6.18.0" \
    "modal>=1.5.0" \
    "treys>=0.1.8"

EXPOSE 7860

CMD ["python", "app.py"]
