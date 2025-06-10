// File: static/main.js (v8.1)

let btcCharts = {};

document.addEventListener("DOMContentLoaded", () => {
  // Tab switching
  document.querySelectorAll("nav.tabs a").forEach(a => {
    a.addEventListener("click", e => {
      e.preventDefault();
      document.querySelectorAll("nav.tabs li").forEach(li => li.classList.remove("active"));
      a.parentElement.classList.add("active");
      document.querySelectorAll(".tab-content").forEach(sec => sec.style.display = "none");
      document.getElementById(a.dataset.tab).style.display = "block";
      if (a.dataset.tab === "market") loadMarket();
      if (a.dataset.tab === "bitcoin") loadBitcoin();
    });
  });
  // Initial load
  loadMarket();
  // Refresh market table every 60 seconds
  setInterval(loadMarket, 60_000);
});

// Formats price per new rules
function formatPrice(val) {
  if (val > 1000) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  } else if (val >= 1) {
    return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  } else {
    return val.toLocaleString(undefined, { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }
}

// Market cap: full value, no decimals
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

// ===== Bitcoin Tab =====
async function loadBitcoin() {
  const k = await (await fetch("/api/bitcoin/kpis")).json();
  document.getElementById("kpi-price").textContent       = `$${k.price.toLocaleString()}`;
  document.getElementById("kpi-change").textContent      = `${k.change_24h.toFixed(2)}%`;
  document.getElementById("kpi-mcap").textContent        = `$${k.market_cap.toLocaleString()}`;
  document.getElementById("kpi-vol").textContent         = `$${k.volume_24h.toLocaleString()}`;
  document.getElementById("kpi-dom").textContent         = `${k.dominance.toFixed(2)}%`;
  document.getElementById("kpi-supply").textContent      = k.circulating_supply.toLocaleString();
  document.getElementById("kpi-max-supply").textContent  = k.max_supply.toLocaleString();
  document.getElementById("kpi-last-updated").textContent = k.last_updated;

  const hist = await (await fetch("/api/bitcoin/history")).json();

  const slice30   = hist.slice(-30);
  const slice90   = hist.slice(-90);
  const slice365  = hist.slice(-365);
  const slice3650 = hist.slice(-3650);

  function render(id, slice) {
    const labels = slice.map(pt => pt.date);
    const prices = slice.map(pt => pt.price);
    const ctx    = document.getElementById(id).getContext("2d");
    if (btcCharts[id]) btcCharts[id].destroy();
    btcCharts[id] = new Chart(ctx, {
      type: 'line',
      data: { labels, datasets: [{ data: prices, fill: false, tension: 0.1 }] },
      options: {
        scales: { x: { ticks: { maxTicksLimit: 10 } }, y: { beginAtZero: false } },
        plugins: { legend: { display: false } },
        elements: { point: { radius: 2 } }
      }
    });
  }

  render('btcChart30d',   slice30);
  render('btcChart90d',   slice90);
  render('btcChart365d',  slice365);
  render('btcChart3650d', slice3650);
}
