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
      if (a.dataset.tab === "proxies") {
        loadProxies();
        if (bitcoinInterval) {
          clearInterval(bitcoinInterval);
          bitcoinInterval = null;
        }
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
  if (val === null || val === undefined) return "-";
  if (val > 1000) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  } else if (val >= 1) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  } else {
    return val.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }
}

function formatMarketCap(val) {
  if (val === null || val === undefined) return "-";
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
        <td>
          <img src="${c.image}" alt="${c.symbol} icon"/>
        </td>
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
        <td>${new Date(c.last_updated).toLocaleString(undefined, { timeZoneName: 'short' })}</td>
      </tr>`;
  }).join('');
}

let btcHistoryCache = null;

async function loadBitcoin() {
  const k = await (await fetch("/api/bitcoin/kpis")).json();

  window.btcATH = k.ath;  // Save ATH for the chart

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
  // Now show last_updated in local timezone with label
  document.getElementById("kpi-last-updated").textContent  =
    k.last_updated
      ? new Date(k.last_updated).toLocaleString(undefined, { timeZoneName: 'short' })
      : '';
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

  // Debug
  console.log("window.btcATH =", window.btcATH, typeof window.btcATH);

  const ath = Number(window.btcATH); // ensure number

  // Register annotation plugin if not already done
  if (window.Chart && window.Chart.registry && window['chartjs-plugin-annotation']) {
    Chart.register(window['chartjs-plugin-annotation']);
  }

  const ctx = document.getElementById("btcChartCombined").getContext("2d");
  if (btcCharts.combined) btcCharts.combined.destroy();

  btcCharts.combined = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ data: prices, fill: false, tension: 0.1 }] },
    options: {
      plugins: {
        legend: { display: false },
        annotation: {
  annotations: {
    athLine: {
      type: 'line',
      yMin: ath,
      yMax: ath,
      borderColor: '#ffdf00',
      borderWidth: 1, 
      borderDash: [6, 6],
      label: {
        display: true,
content: "ATH: " + ath.toLocaleString(undefined, {minimumFractionDigits: 0, maximumFractionDigits: 0}),
        position: 'start',
        backgroundColor: '#222',
        color: '#ffdf00',
        font: {  size: 11 }
      }
    }
  }
}
      },
      scales: {
        x: { ticks: { maxTicksLimit: 10 } },
        y: { beginAtZero: false }
      },
      elements: { point: { radius: 2 } }
    }
  });
}


// ===== Proxies Tab =====
async function loadProxies() {
  const res = await fetch("/api/proxies");
  const data = await res.json();

  // Find latest timestamp for display
  let latest = null;
  data.forEach(row => {
    if (row.last_updated && (!latest || row.last_updated > latest)) latest = row.last_updated;
  });
 
   // Group by type
  const treasuries = data.filter(d => d.type === "treasury");
  const etfs = data.filter(d => d.type === "etf");
  const miners = data.filter(d => d.type === "miner");

  function renderRows(arr) {
    return arr.map(d => `
      <tr>
        <td>${d.ticker}</td>
        <td>${d.name}</td>
        <td>
          ${d.country_flag ? `<img src="${d.country_flag}" alt="" title="${d.country}" style="width:22px;vertical-align:middle;margin-right:4px;">` : ""}
          ${d.country ? d.country : ""}
        </td>
        <td>${d.btc ? d.btc.toLocaleString() : "-"}</td>
        <td>$${d.usd ? d.usd.toLocaleString(undefined, {minimumFractionDigits:0, maximumFractionDigits:0}) : "-"}</td>
        <td>${d.pct_21m ? d.pct_21m : "-"}</td>
        <td>
          ${d.filing_link ? `<a href="${d.filing_link}" target="_blank" rel="noopener" style="color:#2979ff;">Link</a>` : ""}
        </td>
        <td>${d.price !== null ? "$" + d.price : "-"}</td>
        <td>${d.last_updated ? new Date(d.last_updated).toLocaleString(undefined, { timeZoneName: 'short' }) : ""}</td>
      </tr>
    `).join('');
  }

  document.querySelector("#treasuries-table tbody").innerHTML = renderRows(treasuries);
  document.querySelector("#etfs-table tbody").innerHTML = renderRows(etfs);
  document.querySelector("#miners-table tbody").innerHTML = renderRows(miners);
}
