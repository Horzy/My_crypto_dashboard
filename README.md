# Cryptocurrency Dashboard

## Project Overview

This project is a web-based cryptocurrency dashboard built with Python (Flask), JavaScript (Chart.js), and SQLite.  
It provides a live view of the crypto market, focusing on the top 50 cryptocurrencies and in-depth Bitcoin analytics, including key metrics and interactive price history charts.

---

## Project Structure

project_root/
├── app.py # Main Flask backend
├── fetch_and_store.py # Data fetching/storage logic
├── crypto.db # SQLite database (data storage)
├── requirements.txt # Python dependencies
├── .env # API/config environment variables
├── static/
│ ├── style.css # Main CSS styles
│ ├── main.js # All frontend logic (JS)
│ └── index.html # Single-page app UI
├── adhoc_backfill_btc.py # Utility: backfill BTC daily closes
└── adhoc_db_test.py # Utility: DB test script



---

## File Descriptions & Interactions

- **app.py**
  - The main entry point for the Flask web app.
  - Exposes API endpoints for the frontend:
    - `/api/cryptos`: Top 50 coins, used for the market table.
    - `/api/bitcoin/kpis`: Live Bitcoin KPIs (price, market cap, dominance, ATH, 24h change/high/low, etc).
    - `/api/bitcoin/history`: Historical BTC daily closes for charting.
  - Handles periodic background jobs with APScheduler (fetches fresh crypto data every 5 minutes).
  - Communicates with `fetch_and_store.py` for all data operations and SQLite for storage.

- **fetch_and_store.py**
  - Contains all logic to fetch data from CoinGecko.
  - Upserts top 50 coins and Bitcoin metrics into the SQLite database.
  - Exposes helper functions for app.py and daily/adhoc BTC close updates.

- **crypto.db**
  - Local SQLite database, stores:
    - The current top 50 coin stats.
    - Bitcoin’s daily closing prices for history charts.

- **requirements.txt**
  - Python package dependencies for the backend (Flask, APScheduler, requests, etc).

- **.env**
  - API/config variables (CoinGecko URL, currency, page size, DB path).

- **static/index.html**
  - The main (and only) HTML page for the dashboard, using dark mode styling.
  - References main.js and style.css.

- **static/style.css**
  - Styles for all components: tab bar, KPI wrappers, tables, cards, chart controls, and chart area.
  - Orange accent for highlights.

- **static/main.js**
  - Handles all frontend behavior:
    - Fetches API endpoints.
    - Renders the market table, KPIs, and a unified interactive Bitcoin chart.
    - Lets user switch the Bitcoin chart timeframe with orange-accented buttons.
    - Keeps KPIs and chart in sync with the backend.

- **adhoc_backfill_btc.py**
  - Standalone utility for backfilling historical BTC daily close prices using Coinbase Pro candles.
  - Used only for manual DB operations/maintenance.

- **adhoc_db_test.py**
  - Simple utility to query and check the BTC history table in the database.

---

## How the System Works

1. **Backend Scheduler (app.py & fetch_and_store.py):**
   - Every 5 minutes: fetches fresh market data from CoinGecko and updates the SQLite database.
   - Keeps Bitcoin daily closes up-to-date for history.

2. **API Endpoints (app.py):**
   - Serve the latest database data to the frontend via `/api/cryptos`, `/api/bitcoin/kpis`, `/api/bitcoin/history`.

3. **Frontend (main.js + index.html):**
   - Market table and Bitcoin KPIs are polled live every 60 seconds for near-real-time updates.
   - The Bitcoin chart is interactive: users can switch timeframes (30d, 90d, 12mo, 10y) instantly.
   - All visuals styled for clarity with orange/black dark mode.

4. **Utilities:**
   - Ad hoc scripts allow for DB maintenance and manual data recovery (e.g., missed daily closes).

---

## Outstanding Future Developments

- **Expand Bitcoin KPIs:**  
  Consider adding more advanced Bitcoin KPIs (realized cap, volatility, days since ATH, block time, hash rate, etc.) as user needs evolve.

- **Altcoin Detail Views:**  
  Allow users to click on any coin for a detailed breakdown and dedicated chart page.

- **News & Settings Tabs:**  
  Complete the "News" and "Settings" tab functionality, e.g. display live news feeds, let users customize preferences.

- **User Personalization:**  
  Support custom watchlists, coin search/filter, and user preferences.

- **Real-Time Updates:**  
  Migrate from AJAX polling to WebSockets for ultra-live KPI and market data streaming.

- **Frontend Polish:**  
  Improve mobile/responsive layout, accessibility, and add more chart interactivity.

- **Deployment Hardening:**  
  Add production error logging, caching, rate limiting, Dockerization, and full deployment docs.

- **New Data Sources:**  
  Optionally incorporate more sources (Blockchain.com, Bitnodes, CoinMetrics, Blockstream) for technical network metrics.

- **Manual BTC Close Recovery:**  
  Optionally add UI for admins to backfill missed BTC closes in case of downtime.

---

*This README reflects the current state after all recent improvements and UI/UX changes. See code comments for more details or open an issue for new feature ideas!*
