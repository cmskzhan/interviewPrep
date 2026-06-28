import sqlite3
from contextlib import contextmanager
from typing import Dict, Any, List, Iterator

DB_PATH = "market_data.db"


class MarketDataRepository:
    """
    Repository layer for the Market Data Store.

    Handles all SQLite persistence for ingested stock bars.
    """

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS stock_bars (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL,
                    trade_count INTEGER,
                    vwap REAL,
                    trade TEXT,
                    UNIQUE(symbol, timeframe, timestamp)
                )
                """
            )
            # Migrate existing databases that predate the `trade` column.
            existing = {row["name"] for row in conn.execute("PRAGMA table_info(stock_bars)")}
            if "trade" not in existing:
                conn.execute("ALTER TABLE stock_bars ADD COLUMN trade TEXT")

    def save_bars(self, symbol: str, timeframe: str, bars: List[Dict[str, Any]]) -> int:
        """
        Persist a list of bars for a symbol. Returns the number of rows written.

        Uses INSERT OR IGNORE so repeated ingestion of the same bar is idempotent.
        """
        rows = [
            (
                symbol,
                timeframe,
                bar.get("t"),
                bar.get("o"),
                bar.get("h"),
                bar.get("l"),
                bar.get("c"),
                bar.get("v"),
                bar.get("n"),
                bar.get("vw"),
            )
            for bar in bars
        ]

        with self._connect() as conn:
            cursor = conn.executemany(
                """
                INSERT OR IGNORE INTO stock_bars
                    (symbol, timeframe, timestamp, open, high, low, close, volume, trade_count, vwap)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            return cursor.rowcount

    def get_bars(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve stored bars for a symbol, most recent first."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT symbol, timeframe, timestamp, open, high, low, close, volume, trade_count, vwap
                FROM stock_bars
                WHERE symbol = ?
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (symbol, limit),
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_bars_asc(self, symbol: str, timeframe: str = "1D") -> List[Dict[str, Any]]:
        """Retrieve all stored bars for a symbol, oldest first (chronological)."""
        with self._connect() as conn:
            cursor = conn.execute(
                """
                SELECT id, symbol, timeframe, timestamp, open, high, low, close, volume, trade
                FROM stock_bars
                WHERE symbol = ? AND timeframe = ?
                ORDER BY timestamp ASC
                """,
                (symbol, timeframe),
            )
            return [dict(row) for row in cursor.fetchall()]

    def clear_trade_signals(self, symbol: str, timeframe: str = "1D") -> None:
        """Reset the trade column for a symbol so the strategy can recompute cleanly."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE stock_bars SET trade = NULL WHERE symbol = ? AND timeframe = ?",
                (symbol, timeframe),
            )

    def set_trade_signal(self, bar_id: int, signal: str) -> None:
        """Mark a specific bar (by row id) with a trade signal ('buy' or 'sell')."""
        with self._connect() as conn:
            conn.execute(
                "UPDATE stock_bars SET trade = ? WHERE id = ?",
                (signal, bar_id),
            )
