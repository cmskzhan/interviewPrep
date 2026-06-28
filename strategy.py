"""
Trading strategy (Strategy layer of the architecture).

Rule:
    Split the stored bars into consecutive windows of 5 days.
    In each window:
        - mark the date with the lowest `low`  as BUY
        - mark the date with the highest `high` as SELL
    Signals are written back to the `trade` column in SQLite.
"""

from typing import Dict, Any, List

from market_data_repository import MarketDataRepository

WINDOW_SIZE = 5


class MinMaxWindowStrategy:
    """Buy the cheapest day and sell the most expensive day in each 5-day window."""

    def __init__(self, repository: MarketDataRepository, window_size: int = WINDOW_SIZE):
        self.repository = repository
        self.window_size = window_size

    def run(self, symbol: str, timeframe: str = "1D") -> Dict[str, Any]:
        symbol = symbol.upper()
        bars = self.repository.get_bars_asc(symbol, timeframe)

        if not bars:
            return {"symbol": symbol, "windows": 0, "buys": 0, "sells": 0, "signals": []}

        # Start from a clean slate so re-running is idempotent.
        self.repository.clear_trade_signals(symbol, timeframe)

        signals: List[Dict[str, Any]] = []
        buys = sells = windows = 0

        for start in range(0, len(bars), self.window_size):
            window = bars[start:start + self.window_size]
            windows += 1

            buy_bar = min(window, key=lambda b: b["low"])
            sell_bar = max(window, key=lambda b: b["high"])

            self.repository.set_trade_signal(buy_bar["id"], "buy")
            buys += 1
            signals.append({"date": buy_bar["timestamp"], "signal": "buy", "low": buy_bar["low"]})

            # If the same bar is both min-low and max-high, prefer the buy mark and skip sell.
            if sell_bar["id"] != buy_bar["id"]:
                self.repository.set_trade_signal(sell_bar["id"], "sell")
                sells += 1
                signals.append({"date": sell_bar["timestamp"], "signal": "sell", "high": sell_bar["high"]})

        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "window_size": self.window_size,
            "windows": windows,
            "buys": buys,
            "sells": sells,
            "signals": signals,
        }


if __name__ == "__main__":
    repo = MarketDataRepository()
    strategy = MinMaxWindowStrategy(repo)
    result = strategy.run("MSFT")

    print(f"Symbol: {result['symbol']}  windows={result['windows']}  "
          f"buys={result['buys']}  sells={result['sells']}\n")
    for s in result["signals"]:
        price = s.get("low", s.get("high"))
        print(f"  {s['date']}  {s['signal'].upper():<4}  price={price}")
