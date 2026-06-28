# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

**Local dev setup:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" requests
```

**Run market-data-service:**
```bash
uvicorn main:app --reload
```

**Run strategy standalone:**
```bash
python strategy.py
```

**Inspect SQLite data:**
```bash
python sqlite_client.py
```

**Build Docker images (from repo root):**
```bash
docker build -f k8s/market-data-service/Dockerfile -t millenium-market-data-service:latest .
docker build -f k8s/strategy-service/Dockerfile -t millenium-strategy-service:latest .
```

**Terraform (AWS infra):**
```bash
cd terraform && terraform init && terraform plan && terraform apply
```

There is no test suite and no linter configuration in this project.

## Architecture

This is a mock algorithmic trading demo. The conceptual pipeline is:
```
Market Data → Strategy → Risk → OMS → Execution → Portfolio
  (built)      (built)  ───────── not yet implemented ─────
```

### Two microservices

- **market-data-service** (`main.py`, port 8000): ingests OHLCV bars from Alpaca, persists to SQLite, serves cached responses
- **strategy-service** (`k8s/strategy-service/main.py`, port 8001): runs `MinMaxWindowStrategy` over stored bars, writes buy/sell signals back to SQLite

### Layered pattern (Controller → Service → Repository/Client)

| Layer | Files | Role |
|---|---|---|
| Controller | `main.py`, `k8s/strategy-service/main.py` | FastAPI routes; thin; delegates to service |
| Service | `market_data_service.py` | Orchestrates client + repo; owns TTL cache |
| Repository | `market_data_repository.py` | All SQLite I/O; idempotent `INSERT OR IGNORE` |
| Client | `alpaca_client.py` | Wraps Alpaca Market Data v2 REST API |
| Strategy | `strategy.py` (`MinMaxWindowStrategy`) | 5-bar sliding window; marks min-low as `buy`, max-high as `sell` |
| Cache | `cache.py` / `redis_cache.py` | Same `TTLCache` interface; local = in-memory; containers = Redis |

### Cache swap trick

Both Dockerfiles copy `redis_cache.py` → `cache.py` at build time, so `from cache import TTLCache` transparently uses Redis in containers and the in-memory dict locally — no import changes needed.

Cache key format: `investigate:MSFT:1D:30`, TTL 300s. EKS services share an ElastiCache Redis 7.1 cluster, isolated by prefix (`mds:*`, `stg:*`).

### Data flow — market-data-service

`GET /investigate/{symbol}` → `MarketDataIngestionService.investigate()` → TTL cache check → on miss: `AlpacaMarketDataClient.get_stock_bars()` → `MarketDataRepository.save_bars()` → cache store → return.

### Data flow — strategy-service

`POST /run/{symbol}` → `MinMaxWindowStrategy.run()` → load bars ascending → clear old signals → sliding 5-bar windows → write `buy`/`sell` signals. `GET /signals/{symbol}` reads bars where `trade IS NOT NULL`.

### AWS deployment

- **EKS** (k8s 1.30, t3.medium, 2 desired replicas): runs both services
- **DynamoDB**: `millenium-dev-market-data` (PK=symbol, SK=timestamp, 90-day TTL) and `millenium-dev-signals` (PK=symbol, SK=`timestamp#strategy_name`)
- **ElastiCache**: Redis 7.1, TLS (`rediss://`), shared by both services
- **IRSA**: pod identity via OIDC — no static credentials in images

## Key caveats

- `alpaca_client.py` hardcodes a local proxy (`http://127.0.0.1:3128`) and disables SSL verification — development scaffolding only
- `ALPACA_API_KEY` / `ALPACA_API_SECRET` default to demo keys hardcoded in `main.py` and `alpaca_client.py`; override via env vars before real deployment
- `market_data.db` (SQLite binary) is committed to the repo
- `k8s/redis-secret.yaml` contains only a placeholder; the real endpoint is set imperatively from Terraform output at deploy time
- The strategy-service `main.py` lives at `k8s/strategy-service/main.py`, not the root
