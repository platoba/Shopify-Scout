FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import requests; requests.get('https://api.telegram.org', timeout=5)" || exit 1

CMD ["python", "bot.py"]
