FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
RUN useradd -m -u 1000 user
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt kokoro-onnx soundfile gradio_client
COPY --chown=user . .
RUN mkdir -p /data && chown user /data
USER user
ENV AIAC_DATA=/data AIAC_KOKORO_PY=/usr/local/bin/python HF_HOME=/data/hf
EXPOSE 7860
CMD sh -c "python -m uvicorn aiagentcut.server:app --host 0.0.0.0 --port ${PORT:-7860}"
