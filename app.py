import os
import sqlite3
import atexit
import time
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
import requests
from requests.exceptions import HTTPError
from fetch_and_store import (
    fetch_top_coins,
    fetch_global_marketcap,
    upsert_coins,
    update_btc_history,
    upsert_btc_today_close,
)

load_dotenv()
DB_PATH     = os.getenv("DATABASE_PATH", "crypto.db")
API_URL     = os.getenv("API_URL")
GLOBAL_URL  = "https://api.coingecko.com/api/v3/global"
COIN_ID     = "bitcoin"
VS_CURRENCY = os.getenv("VS_CURRENCY", "usd")
PER_PAGE    = 50

# KPI Cache
BTC_KPIS_CACHE = {}
BTC_KPIS_TS    = 0
KPIS_TTL       = 5 * 60  # 5 minutes

# Resilient requests session
session = requests.Session()
session.headers.update({
    "Accept": "application/json",
    "User-Agent": "CryptoDashboard/7.6"
})
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
retry = Retry(total=3, backoff_factor=1,
              status_forcelist=[429,500,502,503,504],
              allowed_methods=["GET"], respect_retry_after_header=True)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

app = Flask(__name__, static_folder="static")
Compress(app)

def scheduled_fetch():
    total = None
    try:
        total = fetch_global_marketcap()
    except Exception as e:
        app.logger.error("Error fetching global market-cap", exc_info=e)

    try:
        coins = fetch_top_coins()
        if total is not None:
            upsert_coins(coins, total)
    except HTTPError as he:
        if he.response.status_code == 429:
            app.logger.warning("Rate limited on top-coins; skipping this cycle.")
        else:
            app.logger.error("HTTP error fetching top-coins", exc_info=he)
    except Exception as e:
        app.logger.error("Unexpected error in scheduled_fetch", exc_info=e)

@app.route("/api/cryptos")
def get_cryptos():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT id, symbol, name, image,
               price, market_cap,
               price_change_1h, price_change_24h,
               price_change_7d, price_change_30d,
               market_cap_share, last_updated
          FROM coins
         ORDER BY market_cap DESC
         LIMIT ?
    """, (PER_PAGE,)).fetchall()
    conn.close()
    keys = ["id", "symbol", "name", "image", "price", "market_cap",
            "price_change_1h", "price_change_24h",
            "price_change_7d", "price_change_30d",
            "market_cap_share", "last_updated"]
    return jsonify([dict(zip(keys, row)) for row in rows])

@app.route("/api/bitcoin/history")
def btc_history():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT date, price FROM btc_history ORDER BY date").fetchall()
    conn.close()
    return jsonify([{"date": r[0], "price": r[1]} for r in rows])

@app.route("/api/bitcoin/kpis")
def btc_kpis():
    global BTC_KPIS_CACHE, BTC_KPIS_TS
    now = time.time()
    if BTC_KPIS_CACHE and now - BTC_KPIS_TS < KPIS_TTL:
        BTC_KPIS_CACHE["last_updated"] = datetime.fromtimestamp(BTC_KPIS_TS).strftime("%Y-%m-%d %H:%M:%S")
        return jsonify(BTC_KPIS_CACHE)

    params = {
      "vs_currency": VS_CURRENCY,
      "ids": COIN_ID,
      "per_page": 1,
      "page": 1,
      "sparkline": "false",
      "price_change_percentage": "1h,24h,7d,30d"
    }
    try:
        # Get basic market data from /coins/markets
        resp = session.get(API_URL, params=params)
        resp.raise_for_status()
        d = resp.json()[0]
        g = session.get(GLOBAL_URL).json().get("data", {})
        total = g.get("total_market_cap", {}).get("usd", 0)
        dom = (d["market_cap"] / total * 100) if total else 0

        # Get ATH from /coins/bitcoin
        btc_info = session.get(
            "https://api.coingecko.com/api/v3/coins/bitcoin",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            }
        ).json()
        ath = btc_info["market_data"]["ath"][VS_CURRENCY]

        BTC_KPIS_CACHE = {
          "price": d["current_price"],
          "change_24h": d["price_change_percentage_24h_in_currency"],
          "market_cap": d["market_cap"],
          "volume_24h": d["total_volume"],
          "circulating_supply": d["circulating_supply"],
          "dominance": dom,
          "high_24h": d["high_24h"],
          "low_24h": d["low_24h"],
          "max_supply": 21000000,
          "ath": ath
        }
        perc_from_ath = ((BTC_KPIS_CACHE["price"] - BTC_KPIS_CACHE["ath"]) / BTC_KPIS_CACHE["ath"]) * 100
        BTC_KPIS_CACHE["from_ath_pct"] = perc_from_ath
        BTC_KPIS_TS = now
        BTC_KPIS_CACHE["last_updated"] = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")

        # Upsert latest BTC close to btc_history
        upsert_btc_today_close(d["current_price"])

    except Exception as e:
        app.logger.error("Error fetching KPIs", exc_info=e)
        if BTC_KPIS_CACHE:
            BTC_KPIS_CACHE["last_updated"] = datetime.fromtimestamp(BTC_KPIS_TS).strftime("%Y-%m-%d %H:%M:%S")

    return jsonify(BTC_KPIS_CACHE or {})

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.add_job(
      func=scheduled_fetch,
      trigger="interval",
      minutes=5,
      id="crypto_fetch_job",
      max_instances=1,
      replace_existing=True
    )
    scheduler.add_job(
      func=update_btc_history,
      trigger="cron",
      hour=0,
      minute=5,
      id="btc_daily_job",
      max_instances=1,
      replace_existing=True
    )
    scheduler.start()
    atexit.register(lambda: scheduler.shutdown(wait=False))

    print("[FLASK] Server running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
