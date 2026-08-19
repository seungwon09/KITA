FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-eng tesseract-ocr-kor \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY docs ./docs
COPY study_ai.sqlite3 /seed/study_ai.sqlite3

RUN useradd --create-home --uid 10001 appuser \
    && mkdir -p /data \
    && chown -R appuser:appuser /app /data /seed

USER appuser

EXPOSE 8002

CMD ["sh", "-c", "if [ -n \"$STUDY_AI_DB_PATH\" ] && [ ! -f \"$STUDY_AI_DB_PATH\" ]; then mkdir -p \"$(dirname \"$STUDY_AI_DB_PATH\")\" && cp /seed/study_ai.sqlite3 \"$STUDY_AI_DB_PATH\"; fi; uvicorn app.main:app --host 0.0.0.0 --port 8002"]
