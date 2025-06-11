import os
import sqlite3
import requests
from datetime import date, datetime, timezone
from dotenv import load_dotenv

load_dotenv()
API_URL      = os.getenv("API_URL")            # e.g. https://api.coingecko.com/api/v3/coins/markets
GLOBAL_URL   = "https://api.coingecko.com/api/v3/global"
VS_CURRENCY  = os.getenv("VS_CURRENCY", "usd")
PER_PAGE     = int(os.getenv("PER_PAGE", 50))
DB_PATH      = os.getenv("DATABASE_PATH", "crypto.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    # Main coins table
    conn.execute("""
    CREATE TABLE IF NOT EXISTS coins (
      id TEXT PRIMARY KEY,
      symbol TEXT,
      name TEXT,
      image TEXT,
      price REAL,
      market_cap REAL,
      price_change_1h REAL,
      price_change_24h REAL,
      price_change_7d REAL,
      price_change_30d REAL,
      market_cap_share REAL,
      last_updated TEXT
    )
    """)
    # Bitcoin daily history
    conn.execute("""
    CREATE TABLE IF NOT EXISTS btc_history (
      date TEXT PRIMARY KEY,
      price REAL
    )
    """)
    return conn

def fetch_global_marketcap():
    resp = requests.get(GLOBAL_URL)
    resp.raise_for_status()
    data = resp.json().get("data", {})
    return data.get("total_market_cap", {}).get("usd", 0.0)

def fetch_top_coins():
    params = {
      "vs_currency": VS_CURRENCY,
      "order": "market_cap_desc",
      "per_page": PER_PAGE,
      "page": 1,
      "sparkline": "false",
      "price_change_percentage": "1h,24h,7d,30d"
    }
    resp = requests.get(API_URL, params=params)
    resp.raise_for_status()
    return resp.json()

def upsert_coins(coins, total_mcap):
    conn = init_db()
    cur = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()
    for c in coins:
        share = (c["market_cap"] / total_mcap * 100) if total_mcap else 0.0
        cur.execute("""
            INSERT INTO coins(
              id, symbol, name, image,
              price, market_cap,
              price_change_1h, price_change_24h,
              price_change_7d, price_change_30d,
              market_cap_share, last_updated
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              image=excluded.image,
              price=excluded.price,
              market_cap=excluded.market_cap,
              price_change_1h=excluded.price_change_1h,
              price_change_24h=excluded.price_change_24h,
              price_change_7d=excluded.price_change_7d,
              price_change_30d=excluded.price_change_30d,
              market_cap_share=excluded.market_cap_share,
              last_updated=excluded.last_updated
        """, (
            c["id"],
            c["symbol"],
            c["name"],
            c["image"],
            c["current_price"],
            c["market_cap"],
            c.get("price_change_percentage_1h_in_currency", 0.0),
            c.get("price_change_percentage_24h_in_currency", 0.0),
            c.get("price_change_percentage_7d_in_currency", 0.0),
            c.get("price_change_percentage_30d_in_currency", 0.0),
            share,
            now_iso,  # Always UTC ISO with offset
        ))
    conn.commit()
    conn.close()

def update_btc_history():
    coins = fetch_top_coins()
    btc = next((c for c in coins if c["id"] == "bitcoin"), None)
    if not btc:
        return
    today = date.today().isoformat()
    price = btc["current_price"]
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
      INSERT OR IGNORE INTO btc_history(date, price)
      VALUES (?, ?)
    """, (today, price))
    conn.commit()
    conn.close()

def upsert_btc_today_close(price):
    today = date.today().isoformat()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO btc_history(date, price)
        VALUES (?, ?)
        ON CONFLICT(date) DO UPDATE SET price=excluded.price
    """, (today, price))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_btc_history()
    print("BTC history updated for", date.today().isoformat())
