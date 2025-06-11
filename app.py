import os
import sqlite3
import atexit
from datetime import datetime, timezone
from flask import Flask, jsonify, send_from_directory
from flask_compress import Compress
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from fetch_and_store import (
    fetch_top_coins,
    fetch_global_marketcap,
    upsert_coins,
    upsert_btc_history_from_coins,
    save_btc_kpis,
    load_btc_kpis,
    fetch_btc_kpis_with_fallback,
    init_db,
    update_proxies_from_bitbo
)

# --- ENV & DB SETUP ---
load_dotenv()
DB_PATH     = os.getenv("DATABASE_PATH", "crypto.db")
PER_PAGE    = 50

print("[DEBUG] Using DB file:", os.path.abspath(DB_PATH))
init_db()   # Ensure all tables exist before anything else

BTC_KPIS_CACHE = {}

app = Flask(__name__, static_folder="static")
Compress(app)

def get_last_ath():
    last = load_btc_kpis()
    return last["ath"] if last and "ath" in last else None

def scheduled_fetch():
    try:
        total = fetch_global_marketcap()
        coins = fetch_top_coins()
        shared_timestamp = datetime.now(timezone.utc).isoformat()
        if total is not None:
            upsert_coins(coins, total, last_updated=shared_timestamp)
        upsert_btc_history_from_coins(coins)
        last_ath = get_last_ath()
        kpis = fetch_btc_kpis_with_fallback(total, shared_timestamp, last_ath)
        if kpis:
            BTC_KPIS_CACHE.clear()
            BTC_KPIS_CACHE.update(kpis)
            save_btc_kpis(kpis)
    except Exception as e:
        app.logger.error("Error in scheduled_fetch", exc_info=e)

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
    if BTC_KPIS_CACHE:
        return jsonify(BTC_KPIS_CACHE)
    kpis = load_btc_kpis()
    if kpis:
        BTC_KPIS_CACHE.update(kpis)
        return jsonify(BTC_KPIS_CACHE)
    return jsonify({"error": "KPI data not available, try again soon."}), 503

@app.route("/api/proxies")
def get_proxies():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT ticker, name, type, btc, usd, price, country, country_flag, pct_21m, filing_link, last_updated
          FROM proxies_latest
    """).fetchall()
    conn.close()
    keys = [
        "ticker", "name", "type", "btc", "usd", "price",
        "country", "country_flag", "pct_21m", "filing_link", "last_updated"
    ]
    return jsonify([dict(zip(keys, row)) for row in rows])

@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")

if __name__ == "__main__":
    import os

    print("[DEBUG] Flask process started | PID:", os.getpid(), "| WERKZEUG_RUN_MAIN:", os.environ.get('WERKZEUG_RUN_MAIN'))

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
        try:
            scheduled_fetch()
            print("[INFO] Forced initial fetch, tabs in sync.")
            update_proxies_from_bitbo()
            print("[INFO] Proxies scraped on startup.")
        except Exception as e:
            print(f"[WARN] Could not perform initial sync: {e}")

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
          func=update_proxies_from_bitbo,
          trigger="interval",
          minutes=60,
          id="proxies_scrape_job",
          max_instances=1,
          replace_existing=True
        )
        scheduler.start()
        atexit.register(lambda: scheduler.shutdown(wait=False))

    print("[FLASK] Server running at http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
