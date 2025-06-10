# Cryptocurrency Dashboard

## Project Goal
This project is a web-based cryptocurrency dashboard built with Python (Flask) and JavaScript. It provides a snapshot of the cryptocurrency market by listing the top 50 cryptocurrencies with key data, and it includes a dedicated Bitcoin section with detailed charts and KPIs (Key Performance Indicators). The goal is to allow users to quickly see the state of the top crypto assets and dive deeper into Bitcoin's performance and metrics via interactive visualizations.

## File Structure
```
project_root/
├── app.py
├── fetch_and_store.py
├── crypto_data.db
├── requirements.txt
├── static/
│   ├── style.css
│   └── main.js
└── templates/
    ├── index.html
    └── bitcoin.html
```

## File Descriptions

- **app.py**: The main Flask application. It initializes the web server, serves static files, and defines routes for API endpoints and pages. Also handles background jobs with APScheduler.
- **fetch_and_store.py**: Responsible for fetching data from CoinGecko, upserting data into the local SQLite database, and (in older versions) for historical backfill logic.
- **crypto_data.db**: The project’s SQLite database. Stores the top 50 cryptocurrencies, their metrics, and a separate table for daily BTC closes.
- **requirements.txt**: Python dependencies.
- **static/index.html**: The HTML template for the dashboard.
- **static/style.css**: CSS styling for the dashboard, charts, tables, and tabs.
- **static/main.js**: JavaScript logic for tab switching, data polling, chart rendering, and formatting.
- **templates/bitcoin.html**: (If used) Alternative or legacy template for the Bitcoin KPIs and charts.

## How It All Fits Together
1. Scheduler fetches fresh data and updates the local DB every 5 minutes.
2. Flask serves API endpoints and static files using the latest DB data.
3. JavaScript fetches and renders market table, Bitcoin KPIs, and charts on the frontend.
4. Charts are rendered with Chart.js; KPIs are cached server-side and updated every 5 min, but the frontend refreshes every 60 seconds for a live feel.

## Future Improvements and Questions
- Add real-time updates with WebSockets or AJAX.
- Expand to support detail views for other coins.
- Optimize large data visualizations.
- Add user preferences and search/filter tools.
- Harden for deployment (caching, error logging, rate-limiting).


## IDEAS TO IMPLEMENT

1. Update BTC daily close logic:
   - Whenever Bitcoin KPIs are fetched (every 5 minutes), write today's BTC price to the btc_history table in the database.
   - Only one price per date should be stored (overwrite or upsert). Do NOT keep multiple prices for the same day.
   - If the date changes (UTC midnight), start writing to the new date automatically.
   - (Low priority, for the future) Consider adding a more detailed database to store higher-frequency prices (e.g., every 5 min) for just the last 7 days.

2. Synchronize Bitcoin KPI fetching:
   - Fetch Bitcoin KPIs from CoinGecko every 5 minutes (same schedule as the Top 50 tab).
   - Cache the KPIs on the backend for 5 minutes.
   - The frontend should poll the KPIs endpoint every 60 seconds for live updates, so users see fresh data as soon as it's available.

3. Expand Bitcoin KPIs:
   - Maintain a list of potential new KPIs (do not prioritize yet; keep the list open).
   - Ideas include: all-time high price, 24h high, days since ATH, realized cap, volatility, etc.
   - Wait to decide which to implement until user prioritizes them.

4. Timestamp on KPIs:
   - Add a timestamp to each KPI, showing when it was last updated.
   - Display the timestamp in a small, non-distracting font.
   - When user is home, review and adjust the design to ensure the timestamp does not distract from the KPI values.

5. Focus on Bitcoin Dominance:
   - Do not add altcoin-dominance or altcoin-centric metrics for now.
   - Bitcoin dominance is important and should be clearly displayed.

6. More Tabs for Expansion:
   - Add a third tab for "Bitcoin proxy companies" (e.g., MicroStrategy, miners, etc.), with tickers, BTC holdings, share price, beta, etc.
   - Add a fourth tab dedicated to "MSTR" (MicroStrategy) with metrics like NAV, BTC/share, company news, charts, etc.
   - User will decide later which companies to include and which KPIs/visualizations are most relevant for each new tab.

7. Open Questions (to revisit later):
   - Should the app allow for *manual* backfilling of missed BTC daily closes if the app is down at midnight?
   - Should the precise UTC time of each KPI and market price be shown, or only the date?
   - Are there any new sources or data providers to consider in addition to CoinGecko?
   - For MSTR tab, should we include side-by-side price vs BTC, or focus on treasury/BTC/share analytics?
