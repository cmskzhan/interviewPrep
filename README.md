# Millennium — Mock Trading Demo

A layered, mock trading application demonstrating market data ingestion, a simple
strategy engine, TTL caching, and a path to a microservices deployment on AWS EKS.

The architecture and design rationale live in [trading_architecture.md](trading_architecture.md).

---

## Architecture at a glance

```
Market Data → Strategy → Risk → OMS → Execution → Portfolio
   (built)     (built)   ─────── not yet implemented ───────
```

Layered design per service: **Controller → Service → Repository / Client**, with a
TTL cache in the service layer shielding external market-data calls.

| Component | Status | Storage (local) | Storage (AWS) |
|-----------|--------|-----------------|---------------|
| Market Data Service | Implemented | SQLite | DynamoDB + ElastiCache |
| Strategy Service | Implemented | SQLite | DynamoDB + ElastiCache |
| Risk / OMS / Execution / Portfolio | Not implemented | — | RDS (planned) |

---

## Project layout

```
.
├── alpaca_client.py            # Client layer — Alpaca Market Data API
├── market_data_repository.py   # Repository layer — SQLite persistence
├── market_data_service.py      # Service layer — ingestion + TTL cache
├── main.py                     # Controller — FastAPI (market-data-service)
├── strategy.py                 # Strategy — min/max 5-day window buy/sell
├── cache.py                    # In-memory TTL cache (local dev)
├── redis_cache.py              # Redis-backed TTL cache (container / EKS)
├── sqlite_client.py            # CLI helper to inspect market_data.db
├── trading_architecture.md     # Architecture & design doc
├── terraform/                  # AWS infra: EKS, DynamoDB, ElastiCache, IAM
└── k8s/                        # Dockerfiles + Kubernetes manifests
    ├── redis-secret.yaml
    ├── market-data-service/
    └── strategy-service/
```

---

## 1. Local development

### Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi "uvicorn[standard]" requests
```

### Run the market-data-service

```bash
uvicorn main:app --reload
```

### Ingest and read market data

```bash
# Trigger ingestion of historical bars into SQLite
curl http://127.0.0.1:8000/investigate/MSFT

# Read stored bars back
curl http://127.0.0.1:8000/bars/MSFT?limit=5

# Health check
curl http://127.0.0.1:8000/health
```

Calling `/investigate/{symbol}` twice within the 300s TTL returns `"cached": true`
on the second call and skips the external Alpaca request.

### Run the strategy

```bash
# Standalone script — computes 5-day min(low)=buy / max(high)=sell signals
python strategy.py
```

### Inspect the database

```bash
# Via the helper script
python sqlite_client.py

# Or directly with the sqlite3 CLI
sqlite3 market_data.db "SELECT timestamp, low, high, trade FROM stock_bars WHERE trade IS NOT NULL ORDER BY timestamp;"
```

---

## 2. Build Docker images

Build from the **repository root** — the build context must include the shared
source files (`cache.py` / `redis_cache.py`, `market_data_repository.py`).

```bash
docker build -f k8s/market-data-service/Dockerfile -t millenium-market-data-service:latest .
docker build -f k8s/strategy-service/Dockerfile     -t millenium-strategy-service:latest .
```

> The Dockerfiles `COPY redis_cache.py cache.py`, so containers use the Redis-backed
> cache while local dev keeps the in-memory `cache.py`. No Python imports change.

---

## 3. Provision AWS infrastructure (Terraform)

Provisions VPC, EKS cluster + node group, DynamoDB tables, ElastiCache (Redis),
and IRSA roles.

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

Key outputs:

```bash
terraform output -raw eks_cluster_name
terraform output -raw redis_primary_endpoint          # sensitive
terraform output -raw market_data_service_role_arn
terraform output -raw strategy_service_role_arn
```

---

## 4. Deploy to EKS

### Connect kubectl to the cluster

```bash
aws eks update-kubeconfig --name "$(terraform -chdir=terraform output -raw eks_cluster_name)"
```

### Create the Redis Secret from the Terraform output

Do **not** commit the real ElastiCache endpoint. Create the Secret at deploy time:

```bash
REDIS_URL=$(terraform -chdir=terraform output -raw redis_primary_endpoint)
kubectl create secret generic redis-credentials \
  --namespace default \
  --from-literal=REDIS_URL="$REDIS_URL"
```

### Fill in deployment placeholders

In both `k8s/*/deployment.yaml` files, replace:

- `<AWS_ACCOUNT_ID>` — in the ECR image URL and the IRSA role ARN annotation
  (role ARNs come from `terraform output -raw market_data_service_role_arn` and
  `strategy_service_role_arn`).

### Apply the manifests

```bash
kubectl apply -f k8s/market-data-service/deployment.yaml
kubectl apply -f k8s/strategy-service/deployment.yaml
```

### Verify

```bash
kubectl get pods
kubectl get svc
kubectl logs deploy/market-data-service
```

---

## Endpoints reference

### market-data-service (port 8000)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/investigate/{symbol}` | Ingest historical bars into the store |
| GET | `/bars/{symbol}` | Read stored bars for a symbol |
| GET | `/health` | Health check |

### strategy-service (port 8001)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/run/{symbol}` | Run the 5-day min/max strategy, persist signals |
| GET | `/signals/{symbol}` | Read bars carrying a buy/sell signal |
| GET | `/health` | Health check |

---

## Areas to improve

### Error handling

The demo intentionally keeps error handling minimal. Three concrete improvements before any real use:

**1. Alpaca client — add a timeout and catch transport errors (`alpaca_client.py:29`)**

`requests.get` has no `timeout=` argument. A hung proxy connection blocks a worker forever. The call also runs behind a hardcoded local proxy (`127.0.0.1:3128`) with TLS verification disabled, so proxy-down scenarios raise a `ConnectionError` or `ProxyError` that is never caught. The upstream handler in `main.py` only catches `HTTPError` (HTTP-level failures), so transport-level failures surface as raw 500s.

Suggested fix: pass `timeout=(connect_seconds, read_seconds)` to `requests.get`, and catch `requests.exceptions.RequestException` (the base class covering connection, timeout, and proxy errors) alongside `HTTPError`, mapping both to a clean `HTTPException`.

**2. Redis cache — fail-open on cache errors (`redis_cache.py`)**

Every `get`/`setex` call can raise `redis.exceptions.ConnectionError` or `TimeoutError`, and neither is caught. A Redis blip takes down ingestion entirely, even though the cache is supposed to be optional. Additionally, `os.environ["REDIS_URL"]` on startup raises `KeyError` if the env var is unset, crashing the service before it serves a single request.

Suggested fix: wrap `get` and `set` in `try/except redis.RedisError` and treat any error as a cache miss (log and continue). Use `os.environ.get("REDIS_URL")` with a clear startup assertion or error message.

**3. Strategy — guard against NULL low/high values (`strategy.py:43-44`)**

`min(window, key=lambda b: b["low"])` does a direct comparison. The schema allows NULL for `low` and `high` (both columns are nullable), and `save_bars` writes `None` for any missing field from the API response. A single bar with a null value causes an uncaught `TypeError: '<' not supported between instances of 'NoneType' and 'float'`.

Suggested fix: filter the window to bars where both `low` and `high` are not `None` before running `min`/`max`, and skip the window if no valid bars remain.

### Logging & metrics

The only observability primitives today are Kubernetes liveness/readiness probes against a static `/health` endpoint and uvicorn's default stdout access log. There is no application logging, no metrics, and no request instrumentation.

**1. Structured application logging (`main.py`, `market_data_service.py`, `strategy.py`, `redis_cache.py`)**

No `logging` module is used anywhere in the service code. Errors become `HTTPException` responses and are silently discarded — there is no record of what failed or why. For containers, stdout is the right sink and stdlib `logging` with a simple JSON or key=value formatter is sufficient with no added dependencies.

Suggested fix: configure a root logger at app startup (one-time setup in `main.py` / `k8s/strategy-service/main.py`) and add `logger.info`/`logger.exception` at the key boundaries: cache hit/miss, Alpaca call start + duration, bars persisted count, strategy signals written count, and any caught exceptions.

**2. Per-request timing and request-ID middleware (`main.py`, `k8s/strategy-service/main.py`)**

Neither FastAPI app registers any middleware. There is no record of request method, path, response status, or latency per call — making it impossible to spot slow requests or error spikes without digging into uvicorn's minimal default access log.

Suggested fix: add a single FastAPI `@app.middleware("http")` in each controller that generates a request ID, records start time, calls `await call_next(request)`, then logs method + path + status + elapsed ms. ~15 lines, no new dependencies.

**3. Meaningful health endpoint (`main.py`, `k8s/strategy-service/main.py`)**

Both `/health` endpoints return `{"status": "ok"}` unconditionally (`main.py:44-46`). They prove the process answers HTTP, but a dead SQLite file, Redis connection failure, or misconfigured env var all still return 200. Both liveness and readiness probes point at the same static endpoint, so a degraded dependency is invisible to Kubernetes.

Suggested fix: have `/health` perform a lightweight dependency check (SQLite `SELECT 1` via the repository's `_connect`, Redis `ping` via the cache client) and return a non-200 status on failure. Optionally split into `/live` (process alive, no deps) and `/ready` (deps reachable) and update the k8s manifests accordingly.

### Retries, timeouts, and thread safety

**1. No timeouts on external calls (`alpaca_client.py:29`, `redis_cache.py:29-31`)**

`requests.get(...)` in `alpaca_client.py` has no `timeout=` argument. A hung Alpaca call or unresponsive proxy at `127.0.0.1:3128` blocks a worker thread indefinitely. Similarly, `redis.Redis.from_url(...)` in `redis_cache.py` sets no `socket_connect_timeout` or `socket_timeout`, so a slow Redis connection also blocks without bound.

Suggested fix: pass `timeout=(connect_seconds, read_seconds)` to `requests.get`; pass `socket_connect_timeout` and `socket_timeout` to `redis.Redis.from_url`. Short values (e.g. 2s connect, 5s read) are appropriate for a demo.

**2. No retry logic anywhere**

No retry or backoff exists on any external call — Alpaca HTTP requests, Redis operations, or SQLite. A single transient failure (Alpaca 429 rate limit, brief Redis blip, momentary network hiccup) propagates immediately as an error with no recovery attempt.

Suggested fix: for Alpaca, a simple manual retry loop (1-2 retries with a short fixed delay) on `requests.exceptions.RequestException` and HTTP 429/5xx is sufficient without adding a retry library. For Redis, treating any error as a cache miss (see error handling fix #2) effectively handles transient blips by simply bypassing the cache.

**3. `TTLCache` is not thread-safe (`cache.py`)**

`cache.py`'s `TTLCache` uses a plain `dict` with no locking. FastAPI runs route handlers on a thread pool, so concurrent requests can race on `get`/`set`/`del`. The most dangerous case is lines 32-33: a thread reads an expired key, another thread deletes it in between, and the first thread then tries to delete it again — raising an uncaught `KeyError`. This only affects local dev; the Redis-backed `redis_cache.py` used in containers does not have this issue since Redis serializes commands server-side.

Suggested fix: wrap `_store` mutations in a `threading.Lock` (acquire on `get`, `set`, and the expiry-eviction branch), or replace the dict with a `threading.local`-aware structure.

**Optional — Prometheus metrics**

A `/metrics` endpoint via `prometheus_client` with counters for ingestion calls, cache hits/misses, strategy runs, and a histogram for Alpaca request latency is the natural next layer. This requires adding `prometheus_client` to requirements and scrape annotations to the k8s pod templates — worthwhile if the cluster already runs a Prometheus stack, but out of scope for a minimal demo.

### Scalability (AWS)

The Terraform provisions a clean horizontally-scalable architecture — on-demand DynamoDB, shared ElastiCache, IRSA roles, multi-replica Deployments. However several gaps prevent the system from actually scaling as designed. Improvements fall into two tiers.

#### Tier 1 — Prerequisite: replace SQLite with DynamoDB

Both Dockerfiles copy `market_data_repository.py` (`import sqlite3`, `DB_PATH = "market_data.db"`) into the container images. Each pod writes to its own ephemeral local file. With `replicas: 2`, the two market-data pods have independent, divergent databases — a `/bars/{symbol}` read returns inconsistent results depending on which pod the Service routes to. More critically, the strategy-service reads from its own empty SQLite file, not the one market-data-service wrote to, so the cross-service data flow is already broken at 2 replicas.

The DynamoDB tables (`millenium-dev-market-data`, `millenium-dev-signals`), IRSA roles, and VPC endpoint are all provisioned by Terraform and ready to use — but no `boto3` code exists in either service (`boto3` is absent from all `requirements.txt` files). No amount of pod or node autoscaling helps while the system of record is a per-pod local file.

Suggested fix: implement a DynamoDB-backed repository (`market_data_repository.py` equivalent using `boto3`) that maps the existing `stock_bars` schema to the provisioned tables (PK=`symbol`, SK=`timestamp`). The IRSA bindings and table definitions are already in place.

#### Tier 2 — Elastic scaling primitives (once Tier 1 is done)

**No pod autoscaling (`k8s/*/deployment.yaml`)**
Replicas are fixed at 2 with no HorizontalPodAutoscaler. CPU requests are defined (`100m` request, `500m` limit), so an HPA on CPU% is structurally possible but `metrics-server` is also not deployed to the cluster. A VerticalPodAutoscaler is also absent.

Suggested fix: deploy `metrics-server` to the cluster and add an HPA targeting ~60% CPU utilisation for each Deployment. Set `minReplicas: 2` and a reasonable `maxReplicas` (e.g. 10).

**No node autoscaling (`terraform/eks.tf`)**
The managed node group has `desired_size = 2`, `max_size = 4` (`eks.tf:77-81`), but no cluster-autoscaler or Karpenter is configured — the node count stays at 2 regardless of pod pressure. The node group also lacks the `k8s.io/cluster-autoscaler/enabled` tag required by the cluster-autoscaler.

Suggested fix: install the AWS Cluster Autoscaler (Helm chart) with an IRSA role, or replace the managed node group with Karpenter NodePools for more flexible bin-packing. Tag the node group appropriately.

**No resilience primitives (`k8s/*/deployment.yaml`)**
There is no PodDisruptionBudget, no `podAntiAffinity`, and no `topologySpreadConstraints`. Both replicas can schedule onto the same node and AZ, making the 2-replica redundancy ineffective. A node drain (`max_unavailable = 1` in `eks.tf:83-85`) can take pods down with no minimum-availability guarantee.

Suggested fix: add a PodDisruptionBudget (`minAvailable: 1`) and a `topologySpreadConstraints` rule spreading pods across nodes and AZs for each Deployment.

**No external ingress**
Both Services are `type: ClusterIP` (`deployment.yaml:79`). The VPC subnets are already tagged for ELB discovery (`vpc.tf:34`, `vpc.tf:48`), but there is no Ingress resource, no AWS Load Balancer Controller, and no external entry point for traffic.

Suggested fix: install the AWS Load Balancer Controller (IRSA role + Helm chart) and add an Ingress resource with `kubernetes.io/ingress.class: alb` annotations to front both services.

#### Infrastructure notes (for production hardening)

- **Single NAT Gateway** (`vpc.tf:59-64`) — all pod egress (e.g. outbound Alpaca API calls) shares one gateway. The comment at `vpc.tf:53` acknowledges "one per AZ for prod." Add a NAT Gateway per AZ to eliminate the SPOF and avoid cross-AZ egress charges.
- **DynamoDB hot partitions** — the partition key is `symbol` on both tables (`dynamodb.tf:10`, `dynamodb.tf:49`). A single heavily-traded ticker concentrates writes on one partition (~1,000 WCU cap under on-demand). For high-throughput symbols, consider a write-sharding suffix on the PK.
- **ElastiCache single-shard** (`elasticache.tf`) — cluster mode is disabled; the setup is primary + 1 replica. This scales reads and provides failover but does not scale writes. Enable cluster mode with multiple shards if write throughput becomes a bottleneck.
- **Only 2 AZs** (`vpc.tf:6`) — the VPC slices subnets across 2 AZs. Expand to 3 for better fault-domain spread.

---

## Notes

- The Alpaca API keys in `main.py` are for the demo only and are overridable via
  the `ALPACA_API_KEY` / `ALPACA_API_SECRET` environment variables. Rotate and move
  to a Secret before any real deployment.
- Pods authenticate to DynamoDB and ElastiCache via IRSA — no static AWS
  credentials are baked into images.
- Local dev uses an in-process cache (`cache.py`), which would be per-pod and
  unshared if deployed. In EKS, containers use `redis_cache.py` so all replicas
  share one ElastiCache cluster, with keys namespaced per service (`mds:*`, `stg:*`).
- With ElastiCache (cache) and DynamoDB (data) holding all state, the service pods
  are fully stateless — they can be scaled, restarted, or rescheduled freely. No
  StatefulSets or PersistentVolumes are required for these two services.
