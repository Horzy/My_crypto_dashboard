import os
import sqlite3
import requests
import json
from datetime import date, datetime, timezone
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()
API_URL      = os.getenv("API_URL")
GLOBAL_URL   = "https://api.coingecko.com/api/v3/global"
VS_CURRENCY  = os.getenv("VS_CURRENCY", "usd")
PER_PAGE     = int(os.getenv("PER_PAGE", 50))
DB_PATH      = os.getenv("DATABASE_PATH", "crypto.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    conn.execute("""
    CREATE TABLE IF NOT EXISTS btc_history (
      date TEXT PRIMARY KEY,
      price REAL
    )
    """)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS btc_kpis (
      id INTEGER PRIMARY KEY CHECK (id = 1),
      price REAL,
      change_24h REAL,
      market_cap REAL,
      volume_24h REAL,
      circulating_supply REAL,
      dominance REAL,
      high_24h REAL,
      low_24h REAL,
      max_supply REAL,
      ath REAL,
      from_ath_pct REAL,
      last_updated TEXT
    )
    """)
    # Proxies with new fields
    conn.execute("""
    CREATE TABLE IF NOT EXISTS proxies_latest (
      ticker TEXT PRIMARY KEY,
      name TEXT,
      type TEXT,
      btc REAL,
      usd REAL,
      price REAL,
      country TEXT,
      country_flag TEXT,
      pct_21m TEXT,
      filing_link TEXT,
      last_updated TEXT
    )
    """)
    return conn

def fetch_global_marketcap():
    try:
        resp = requests.get(GLOBAL_URL, timeout=10)
        if resp.status_code == 429:
            print("[WARN] CoinGecko rate-limited (429) in fetch_global_marketcap.")
            return None
        resp.raise_for_status()
        data = resp.json().get("data", {})
        return data.get("total_market_cap", {}).get("usd", 0.0)
    except Exception as e:
        print("[ERR] Failed to fetch global market cap:", e)
        return None

def fetch_top_coins():
    params = {
      "vs_currency": VS_CURRENCY,
      "order": "market_cap_desc",
      "per_page": PER_PAGE,
      "page": 1,
      "sparkline": "false",
      "price_change_percentage": "1h,24h,7d,30d"
    }
    resp = requests.get(API_URL, params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def upsert_coins(coins, total_mcap, last_updated):
    conn = init_db()
    cur = conn.cursor()
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
            last_updated,
        ))
    conn.commit()
    conn.close()

def upsert_btc_history_from_coins(coins):
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

def save_btc_kpis(kpis: dict):
    conn = init_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO btc_kpis (
          id, price, change_24h, market_cap, volume_24h, circulating_supply, dominance,
          high_24h, low_24h, max_supply, ath, from_ath_pct, last_updated
        ) VALUES (
          1, :price, :change_24h, :market_cap, :volume_24h, :circulating_supply, :dominance,
          :high_24h, :low_24h, :max_supply, :ath, :from_ath_pct, :last_updated
        )
        ON CONFLICT(id) DO UPDATE SET
          price=excluded.price,
          change_24h=excluded.change_24h,
          market_cap=excluded.market_cap,
          volume_24h=excluded.volume_24h,
          circulating_supply=excluded.circulating_supply,
          dominance=excluded.dominance,
          high_24h=excluded.high_24h,
          low_24h=excluded.low_24h,
          max_supply=excluded.max_supply,
          ath=excluded.ath,
          from_ath_pct=excluded.from_ath_pct,
          last_updated=excluded.last_updated
    """, kpis)
    conn.commit()
    conn.close()

def load_btc_kpis():
    conn = init_db()
    cur = conn.cursor()
    row = cur.execute("""
        SELECT price, change_24h, market_cap, volume_24h, circulating_supply, dominance,
               high_24h, low_24h, max_supply, ath, from_ath_pct, last_updated
          FROM btc_kpis WHERE id = 1
    """).fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "price", "change_24h", "market_cap", "volume_24h", "circulating_supply", "dominance",
        "high_24h", "low_24h", "max_supply", "ath", "from_ath_pct", "last_updated"
    ]
    return dict(zip(keys, row))

def fetch_btc_kpis_with_fallback(total_mcap, shared_timestamp, last_ath=None):
    try:
        resp = requests.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            },
            timeout=10
        )
        resp.raise_for_status()
        btc_info = resp.json()
        mkt = btc_info["market_data"]
        ath_val = mkt["ath"]["usd"]
        price = mkt["current_price"]["usd"]
        kpis = {
            "price": price,
            "change_24h": mkt["price_change_percentage_24h_in_currency"]["usd"],
            "market_cap": mkt["market_cap"]["usd"],
            "volume_24h": mkt["total_volume"]["usd"],
            "circulating_supply": mkt["circulating_supply"],
            "dominance": (mkt["market_cap"]["usd"] / total_mcap * 100) if total_mcap else 0.0,
            "high_24h": mkt["high_24h"]["usd"],
            "low_24h": mkt["low_24h"]["usd"],
            "max_supply": mkt["max_supply"] if mkt["max_supply"] else 21000000,
            "ath": ath_val,
            "from_ath_pct": ((price - ath_val) / ath_val) * 100 if ath_val else 0.0,
            "last_updated": shared_timestamp
        }
        return kpis
    except requests.exceptions.HTTPError as e:
        print("[ERR] CoinGecko HTTPError:", e)
        last_kpis = load_btc_kpis()
        if last_kpis:
            print("[INFO] Using last known BTC KPIs from DB as fallback.")
            return last_kpis
        else:
            print("[FATAL] No BTC KPI data available at all!")
            return None
    except Exception as e:
        print("[ERR] Error fetching BTC KPIs:", e)
        last_kpis = load_btc_kpis()
        if last_kpis:
            print("[INFO] Using last known BTC KPIs from DB as fallback.")
            return last_kpis
        else:
            print("[FATAL] No BTC KPI data available at all!")
            return None

def update_proxies_from_bitbo(curated_json_path="curated_proxy.json"):
    """
    Scrape Bitbo treasuries and update the proxies_latest table
    with only the tickers listed in curated_proxy.json (keys must match Bitbo's Symbol:Exchange).
    """
    with open(curated_json_path, "r", encoding="utf-8") as f:
        curated = json.load(f)
    curated_tickers = set(curated.keys())

    url = "https://bitbo.io/treasuries/"
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = soup.select("table.treasuries-table tbody tr")
    found = {}

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 7:
            continue
        name = cols[0].get_text(strip=True)
        ticker = cols[2].get_text(strip=True)
        btc_str = cols[4].get_text(strip=True).replace(",", "")
        usd_str = cols[5].get_text(strip=True).replace(",", "").replace("$", "")
        pct_21m = cols[6].get_text(strip=True)
        country_flag_img = cols[1].find("img")["src"] if cols[1].find("img") else None
        country_code = cols[1].find("img")["data-tooltip"] if cols[1].find("img") else None
        filing_link = cols[3].find("a")["href"] if cols[3].find("a") else None

        if not ticker or ticker not in curated_tickers:
            continue

        btc = float(btc_str) if btc_str else 0.0
        usd = float(usd_str) if usd_str else 0.0
        type_ = curated[ticker].get("type", "unknown")
        custom_name = curated[ticker].get("name", name)
        found[ticker] = {
            "name": custom_name,
            "type": type_,
            "btc": btc,
            "usd": usd,
            "price": None,
            "country": country_code,
            "country_flag": country_flag_img,
            "pct_21m": pct_21m,
            "filing_link": filing_link,
            "last_updated": datetime.utcnow().isoformat()
        }

    # DB migration: add columns if missing
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    for coldef in [
        ("country", "TEXT"),
        ("country_flag", "TEXT"),
        ("pct_21m", "TEXT"),
        ("filing_link", "TEXT")
    ]:
        try:
            cur.execute(f"ALTER TABLE proxies_latest ADD COLUMN {coldef[0]} {coldef[1]}")
        except sqlite3.OperationalError:
            pass
    for ticker, entry in found.items():
        cur.execute("""
            INSERT INTO proxies_latest
                (ticker, name, type, btc, usd, price, country, country_flag, pct_21m, filing_link, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticker) DO UPDATE SET
                name=excluded.name,
                type=excluded.type,
                btc=excluded.btc,
                usd=excluded.usd,
                price=excluded.price,
                country=excluded.country,
                country_flag=excluded.country_flag,
                pct_21m=excluded.pct_21m,
                filing_link=excluded.filing_link,
                last_updated=excluded.last_updated
        """, (
            ticker,
            entry["name"],
            entry["type"],
            entry["btc"],
            entry["usd"],
            entry["price"],
            entry["country"],
            entry["country_flag"],
            entry["pct_21m"],
            entry["filing_link"],
            entry["last_updated"]
        ))
    conn.commit()
    conn.close()
    print(f"[PROXIES] Updated {len(found)} proxies from Bitbo")

    return found

if __name__ == "__main__":
    init_db()
    print("DB initialized.")
