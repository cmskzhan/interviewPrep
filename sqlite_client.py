import sqlite3
from market_data_repository import DB_PATH


def inspect_db(db_path: str = DB_PATH) -> None:
    """Print a summary of the market data stored in SQLite."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        # List tables
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            )
        ]
        print(f"Database: {db_path}")
        print(f"Tables: {tables}\n")

        if "stock_bars" not in tables:
            print("No 'stock_bars' table found. Run an ingestion first.")
            return

        # Total row count
        total = conn.execute("SELECT COUNT(*) AS c FROM stock_bars").fetchone()["c"]
        print(f"Total bars: {total}\n")

        # Per-symbol summary
        print("Per-symbol summary:")
        summary = conn.execute(
            """
            SELECT symbol,
                   timeframe,
                   COUNT(*) AS bars,
                   MIN(timestamp) AS first_ts,
                   MAX(timestamp) AS last_ts
            FROM stock_bars
            GROUP BY symbol, timeframe
            ORDER BY symbol
            """
        ).fetchall()
        for row in summary:
            print(
                f"  {row['symbol']:<8} {row['timeframe']:<5} "
                f"bars={row['bars']:<5} {row['first_ts']} -> {row['last_ts']}"
            )

        # Most recent rows
        print("\nMost recent 10 bars:")
        rows = conn.execute(
            """
            SELECT symbol, timeframe, timestamp, open, high, low, close, volume
            FROM stock_bars
            ORDER BY timestamp DESC
            LIMIT 10
            """
        ).fetchall()
        for row in rows:
            print(
                f"  {row['symbol']:<6} {row['timestamp']} "
                f"O={row['open']} H={row['high']} L={row['low']} "
                f"C={row['close']} V={row['volume']}"
            )
    finally:
        conn.close()


if __name__ == "__main__":
    inspect_db()
