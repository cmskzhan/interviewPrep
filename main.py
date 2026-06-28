import os

from fastapi import FastAPI, HTTPException
from requests import HTTPError

from alpaca_client import AlpacaMarketDataClient
from market_data_repository import MarketDataRepository
from market_data_service import MarketDataIngestionService

# --- Configuration (override via environment variables) ---
ALPACA_API_KEY = os.environ.get("ALPACA_API_KEY", "PKUHDFPCOWWRTNXONIXWJCCWGB")
ALPACA_API_SECRET = os.environ.get("ALPACA_API_SECRET", "Y3LybAFCTpZAWNKcC4CVgaTeydqZtwmAu2nmeWGquK9")

# --- Wire up the layers (Client -> Repository -> Service) ---
client = AlpacaMarketDataClient(api_key=ALPACA_API_KEY, api_secret=ALPACA_API_SECRET)
repository = MarketDataRepository()
service = MarketDataIngestionService(client=client, repository=repository)

app = FastAPI(title="Millennium Trading - Market Data Store")


@app.get("/investigate/{symbol}")
def investigate(symbol: str, timeframe: str = "1D", lookback_days: int = 30):
    """
    Trigger market data ingestion for a symbol.

    Fetches historical bars from Alpaca and stores them in SQLite.
    """
    try:
        result = service.investigate(symbol=symbol, timeframe=timeframe, lookback_days=lookback_days)
    except HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else 502
        raise HTTPException(status_code=status, detail=f"Market data provider error: {exc}")

    return {"status": "ingested", **result}


@app.get("/bars/{symbol}")
def get_bars(symbol: str, limit: int = 100):
    """Read back stored bars for a symbol from the market data store."""
    return repository.get_bars(symbol.upper(), limit=limit)


@app.get("/health")
def health():
    return {"status": "ok"}
