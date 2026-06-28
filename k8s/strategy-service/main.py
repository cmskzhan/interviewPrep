from fastapi import FastAPI, HTTPException

from market_data_repository import MarketDataRepository
from strategy import MinMaxWindowStrategy

repository = MarketDataRepository()
strategy_runner = MinMaxWindowStrategy(repository)

app = FastAPI(title="Millennium Trading - Strategy Service")


@app.post("/run/{symbol}")
def run_strategy(symbol: str, timeframe: str = "1D"):
    """
    Run the min/max window strategy for a symbol and persist signals.
    Bars must already be ingested via market-data-service before calling this.
    """
    result = strategy_runner.run(symbol=symbol, timeframe=timeframe)
    if result["windows"] == 0:
        raise HTTPException(
            status_code=404,
            detail=f"No bars found for {symbol.upper()}. Run ingestion first via market-data-service."
        )
    return result


@app.get("/signals/{symbol}")
def get_signals(symbol: str, timeframe: str = "1D"):
    """Read back bars that carry a trade signal (buy/sell) for a symbol."""
    bars = repository.get_bars_asc(symbol.upper(), timeframe)
    signals = [b for b in bars if b.get("trade")]
    return {"symbol": symbol.upper(), "timeframe": timeframe, "signals": signals}


@app.get("/health")
def health():
    return {"status": "ok"}
