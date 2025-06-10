let btcCharts = {};
let bitcoinInterval = null;
let btcCurrentTimeframe = 30; // default

document.addEventListener("DOMContentLoaded", () => {
  // Tab switching
  document.querySelectorAll("nav.tabs a").forEach(a => {
    a.addEventListener("click", e => {
      e.preventDefault();
      document.querySelectorAll("nav.tabs li").forEach(li => li.classList.remove("active"));
      a.parentElement.classList.add("active");
      document.querySelectorAll(".tab-content").forEach(sec => sec.style.display = "none");
      document.getElementById(a.dataset.tab).style.display = "block";
      if (a.dataset.tab === "market") {
        loadMarket();
        if (bitcoinInterval) {
          clearInterval(bitcoinInterval);
          bitcoinInterval = null;
        }
      }
      if (a.dataset.tab === "bitcoin") {
        loadBitcoin();
        if (bitcoinInterval) clearInterval(bitcoinInterval);
        bitcoinInterval = setInterval(loadBitcoin, 60_000);
      }
    });
  });

  // Initial load
  loadMarket();

  // Refresh market table every 60 seconds
  setInterval(loadMarket, 60_000);

  // If Bitcoin tab is active by default (for direct links)
  if (document.querySelector("nav.tabs li.active a").dataset.tab === "bitcoin") {
    loadBitcoin();
    if (bitcoinInterval) clearInterval(bitcoinInterval);
    bitcoinInterval = setInterval(loadBitcoin, 60_000);
  }

  // Timeframe button logic for Bitcoin chart
  document.querySelectorAll('.tf-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.tf-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      btcCurrentTimeframe = parseInt(btn.getAttribute('data-tf'));
      renderCombinedChart();
    });
  });
  // Set initial active button
  let initialBtn = document.querySelector('.tf-btn[data-tf="30"]');
  if (initialBtn) initialBtn.classList.add('active');
});

window.addEventListener("beforeunload", () => {
  if (bitcoinInterval) clearInterval(bitcoinInterval);
});

function formatPrice(val) {
  if (val > 1000) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  } else if (val >= 1) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  } else {
    return val.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }
}

function formatMarketCap(val) {
  return val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

// ===== Market Tab =====
async function loadMarket() {
  const res  = await fetch("/api/cryptos");
  const data = await res.json();
  const tbody = document.querySelector("#crypto-table tbody");
  tbody.innerHTML = data.map((c, i) => {
    const isBTC = c.symbol.toLowerCase() === 'btc';
    const fmtChange = v =>
      `<td class="${v >= 0 ? 'positive' : 'negative'}">${v.toFixed(2)}%</td>`;
    return `
      <tr class="${isBTC ? 'bitcoin-row' : ''}">
        <td>${i + 1}</td>
        <td>${c.name}</td>
        <td>${c.symbol.toUpperCase()}</td>
        <td>$${formatPrice(c.price)}</td>
        <td>$${formatMarketCap(c.market_cap)}</td>
        ${fmtChange(c.price_change_1h)}
        ${fmtChange(c.price_change_24h)}
        ${fmtChange(c.price_change_7d)}
        ${fmtChange(c.price_change_30d)}
        <td class="market-share-cell">
          <span>${c.market_cap_share.toFixed(2)}%</span>
          <div class="bar"><div class="fill" style="width:${c.market_cap_share}%"></div></div>
        </td>
        <td>${new Date(c.last_updated).toLocaleString()}</td>
      </tr>`;
  }).join('');
}

let btcHistoryCache = null;

async function loadBitcoin() {
  const k = await (await fetch("/api/bitcoin/kpis")).json();
  document.getElementById("kpi-price").textContent         = `$${k.price.toLocaleString()}`;
  document.getElementById("kpi-change").textContent        = `${k.change_24h.toFixed(2)}%`;
  document.getElementById("kpi-mcap").textContent          = `$${k.market_cap.toLocaleString()}`;
  document.getElementById("kpi-vol").textContent           = `$${k.volume_24h.toLocaleString()}`;
  document.getElementById("kpi-dom").textContent           = `${k.dominance.toFixed(2)}%`;
  document.getElementById("kpi-supply").textContent        = k.circulating_supply.toLocaleString();
  document.getElementById("kpi-max-supply").textContent    = k.max_supply.toLocaleString();
  document.getElementById("kpi-ath").textContent           = `$${k.ath.toLocaleString()}`;
  document.getElementById("kpi-from-ath-pct").textContent  = `${k.from_ath_pct.toFixed(2)}%`;
  document.getElementById("kpi-high24h").textContent       = `$${k.high_24h.toLocaleString()}`;
  document.getElementById("kpi-low24h").textContent        = `$${k.low_24h.toLocaleString()}`;
  document.getElementById("kpi-last-updated").textContent  = k.last_updated;

  btcHistoryCache = await (await fetch("/api/bitcoin/history")).json();
  renderCombinedChart();
}

// Unified chart render function
function renderCombinedChart() {
  if (!btcHistoryCache) return;
  const tf = btcCurrentTimeframe;
  let dataSlice = [];
  if (tf === 30) dataSlice = btcHistoryCache.slice(-30);
  else if (tf === 90) dataSlice = btcHistoryCache.slice(-90);
  else if (tf === 365) dataSlice = btcHistoryCache.slice(-365);
  else dataSlice = btcHistoryCache.slice(-3650);

  const labels = dataSlice.map(pt => pt.date);
  const prices = dataSlice.map(pt => pt.price);
  const ctx = document.getElementById("btcChartCombined").getContext("2d");

  if (btcCharts.combined) btcCharts.combined.destroy();

  btcCharts.combined = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ data: prices, fill: false, tension: 0.1 }] },
    options: {
      scales: { x: { ticks: { maxTicksLimit: 10 } }, y: { beginAtZero: false } },
      plugins: { legend: { display: false } },
      elements: { point: { radius: 2 } }
    }
  });
}
