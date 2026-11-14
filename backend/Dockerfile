FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/tmp/labmirror

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY labmirror ./labmirror

# One worker only: the job queue is in-process memory.
CMD ["sh", "-c", "uvicorn labmirror.api:app --host 0.0.0.0 --port ${PORT:-10000} --workers 1"]
