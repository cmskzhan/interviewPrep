# Build context must be the repo root so shared source files are accessible:
#   docker build -f k8s/strategy-service/Dockerfile -t millenium-strategy-service:latest .

FROM python:3.12-slim

WORKDIR /app

COPY k8s/strategy-service/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Shared modules
# redis_cache.py is copied as cache.py so existing imports work unchanged in the container.
# Local dev continues to use the in-memory cache.py.
COPY redis_cache.py cache.py
COPY market_data_repository.py .

# Service-owned modules
COPY strategy.py .
COPY k8s/strategy-service/main.py .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
