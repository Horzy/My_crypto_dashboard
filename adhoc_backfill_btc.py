# File: backfill_btc.py

import os
import sqlite3
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
DB_PATH = os.getenv("DATABASE_PATH", "crypto.db")

def backfill_history():
    # Coinbase Pro daily candles endpoint
    url = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
    # Create the table if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS btc_history (
            date TEXT PRIMARY KEY,
            price REAL
        )
    """)
    conn.commit()

    # Page through history in 300-day chunks (max per request)
    start_date = datetime(2015, 1, 1)      # Coinbase Pro has reliable data from ~2015
    end_date   = datetime.utcnow()
    chunk      = timedelta(days=300)
    inserted   = 0

    cursor = start_date
    while cursor < end_date:
        chunk_start = cursor
        chunk_end   = min(cursor + chunk, end_date)
        params = {
            "start": chunk_start.isoformat(),
            "end":   chunk_end  .isoformat(),
            "granularity": 86400  # one-day candles
        }
        print(f"Fetching {chunk_start.date()} → {chunk_end.date()}…")
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        candles = resp.json()  # each: [ time, low, high, open, close, volume ]

        for ts, low, high, o, close, vol in candles:
            date_str = datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            cur.execute(
                "INSERT OR IGNORE INTO btc_history(date, price) VALUES (?, ?)",
                (date_str, close)
            )
            if cur.rowcount:
                inserted += 1

        conn.commit()
        cursor = chunk_end + timedelta(seconds=1)

    conn.close()
    print(f"Done! Inserted {inserted} new rows into btc_history.")

if __name__ == "__main__":
    backfill_history()
