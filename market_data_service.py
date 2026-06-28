from datetime import datetime, timedelta, timezone
from typing import Any

from alpaca_client import AlpacaMarketDataClient
from market_data_repository import MarketDataRepository
from cache import TTLCache, DEFAULT_TTL_SECONDS


class MarketDataIngestionService:
    """
    Service layer for Market Data Ingestion.

    Orchestrates the workflow:
        Alpaca client (external API)  ->  normalize  ->  repository (SQLite store)

    Results are cached with a TTL so repeated requests for the same
    symbol/timeframe/lookback within the TTL window skip the external call.
    """

    def __init__(
        self,
        client: AlpacaMarketDataClient,
        repository: MarketDataRepository,
        cache: TTLCache | None = None,
    ):
        self.client = client
        self.repository = repository
        self.cache = cache if cache is not None else TTLCache(ttl_seconds=DEFAULT_TTL_SECONDS)

    def investigate(self, symbol: str, timeframe: str = "1D", lookback_days: int = 30) -> dict[str, Any]:
        """
        Ingest historical bars for a symbol into the market data store.

        Returns a summary of what was ingested. Cached for the cache TTL.
        """
        symbol = symbol.upper()
        cache_key = TTLCache.build_key("investigate", symbol, timeframe, lookback_days)

        cached = self.cache.get(cache_key)
        if cached is not None:
            return {**cached, "cached": True}

        start = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).strftime("%Y-%m-%dT%H:%M:%SZ")

        response = self.client.get_stock_bars(symbol=symbol, timeframe=timeframe, start=start)
        bars = response.get("bars") or []

        rows_written = self.repository.save_bars(symbol, timeframe, bars)

        result = {
            "symbol": symbol,
            "timeframe": timeframe,
            "start": start,
            "bars_received": len(bars),
            "rows_written": rows_written,
            "cached": False,
        }
        self.cache.set(cache_key, result)
        return result
