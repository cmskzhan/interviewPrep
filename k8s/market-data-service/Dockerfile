# Build context must be the repo root so shared source files are accessible:
#   docker build -f k8s/market-data-service/Dockerfile -t millenium-market-data-service:latest .

FROM python:3.12-slim

WORKDIR /app

COPY k8s/market-data-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared modules
# redis_cache.py is copied as cache.py so existing imports work unchanged in the container.
# Local dev continues to use the in-memory cache.py.
COPY redis_cache.py cache.py
COPY market_data_repository.py .

# Service-owned modules
COPY alpaca_client.py .
COPY market_data_service.py .
COPY main.py .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
