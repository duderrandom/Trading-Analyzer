/*
 * Trading Strategy Analyzer — frontend client.
 * Vanilla JS, no build step. Talks to the FastAPI backend.
 */
(() => {
  "use strict";

  // ─── Config ───────────────────────────────────────────────────────
  const API_BASE = (() => {
    // Allow overriding via ?api=http://host:port for deployment flexibility.
    const fromQuery = new URLSearchParams(location.search).get("api");
    const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
    return (fromQuery || (isLocal ? "http://localhost:8000" : "")).replace(/\/$/, "");
  })();

  // Per-strategy display colors (match CSS variables).
  const STRATEGY_COLORS = {
    buy_hold:     "#4ea1ff",
    ma_crossover: "#2fd48f",
    rsi:          "#f6b93b",
    custom:       "#c084fc",
  };
  const FALLBACK_COLOR = "#c4c6cc";

  // ─── DOM shortcuts ────────────────────────────────────────────────
  const $ = (id) => document.getElementById(id);
  const form           = $("backtestForm");
  const strategyList   = $("strategyList");
  const resultsEl      = $("results");
  const emptyState     = $("emptyState");
  const errorMsg       = $("errorMsg");
  const runBtn         = $("runBtn");
  const exportBtn      = $("exportBtn");
  const metricsTbody   = document.querySelector("#metricsTable tbody");
  const tradesTbody    = document.querySelector("#tradesTable tbody");
  const priceSelect    = $("priceStrategySelect");
  const bestBanner     = $("bestBanner");
  const apiStatus      = $("apiStatus");
  const apiBase        = $("apiBase");
  const apiDocsLink    = $("apiDocsLink");

  apiBase.textContent = API_BASE;
  apiDocsLink.href    = `${API_BASE}/docs`;

  // ─── State ────────────────────────────────────────────────────────
  let equityChart = null;
  let priceChart  = null;
  let lastResponse = null;

  // ─── Helpers ──────────────────────────────────────────────────────
  const fmtMoney = (n) =>
    n == null ? "—" :
    n.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

  const fmtPct = (n) => {
    if (n == null) return "—";
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(2)}%`;
  };

  const fmtNum = (n, digits = 2) => (n == null ? "—" : n.toFixed(digits));

  const pctClass = (n) => (n > 0 ? "pos" : n < 0 ? "neg" : "muted-cell");

  const setError = (msg) => {
    if (!msg) { errorMsg.hidden = true; errorMsg.textContent = ""; return; }
    errorMsg.hidden = false;
    errorMsg.textContent = msg;
  };

  const colorFor = (id) => STRATEGY_COLORS[id] || FALLBACK_COLOR;

  // ─── Date helpers ─────────────────────────────────────────────────
  function defaultDateRange() {
    const end = new Date();
    const start = new Date();
    start.setFullYear(start.getFullYear() - 3);
    return { start: start.toISOString().slice(0, 10), end: end.toISOString().slice(0, 10) };
  }

  // ─── API calls ────────────────────────────────────────────────────
  async function apiGet(path) {
    const resp = await fetch(`${API_BASE}${path}`);
    if (!resp.ok) throw new Error(`${resp.status} ${resp.statusText}`);
    return resp.json();
  }

  async function apiPost(path, body, asBlob = false) {
    const resp = await fetch(`${API_BASE}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      let detail = `${resp.status} ${resp.statusText}`;
      try {
        const j = await resp.json();
        if (j && j.detail) detail = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
      } catch (_) { /* body may not be JSON */ }
      throw new Error(detail);
    }
    return asBlob ? resp.blob() : resp.json();
  }

  async function checkApiStatus() {
    try {
      await apiGet("/");
      apiStatus.classList.add("ok");
      apiStatus.classList.remove("down");
      apiStatus.querySelector(".label").textContent = "connected";
    } catch (_) {
      apiStatus.classList.remove("ok");
      apiStatus.classList.add("down");
      apiStatus.querySelector(".label").textContent = "offline";
    }
  }

  async function loadStrategies() {
    try {
      const strategies = await apiGet("/api/strategies");
      strategyList.innerHTML = "";
      strategies.forEach((s, i) => {
        const wrap = document.createElement("label");
        wrap.className = "strategy-item";
        wrap.style.borderLeft = `3px solid ${colorFor(s.id)}`;
        wrap.innerHTML = `
          <input type="checkbox" name="strategy" value="${s.id}" ${i < 3 ? "checked" : ""} />
          <div>
            <div class="name">${s.label}</div>
            <div class="desc">${s.description}</div>
          </div>`;
        strategyList.appendChild(wrap);
      });
    } catch (e) {
      strategyList.innerHTML = `<p class="error" style="margin:0">Couldn't reach the backend at <code>${API_BASE}</code>. Is it running?</p>`;
    }
  }

  // ─── Custom strategy builder ──────────────────────────────────────
  function indicatorNode(kind, period) {
    if (kind === "close") return { price: "close" };
    if (kind === "rsi")   return { ind: "rsi", period };
    return { ind: kind, period };  // sma | ema
  }

  function compileRule(ruleEl) {
    const leftKind = ruleEl.querySelector(".custom-left-ind").value;
    const leftPer  = +ruleEl.querySelector(".custom-left-period").value;
    const op       = ruleEl.querySelector(".custom-op").value;
    const rightKind = ruleEl.querySelector(".custom-right-kind").value;

    let right;
    if (rightKind === "const") {
      right = { const: +ruleEl.querySelector(".custom-right-const").value };
    } else {
      const rIndKind = ruleEl.querySelector(".custom-right-ind").value;
      const rPer     = +ruleEl.querySelector(".custom-right-period").value;
      right = indicatorNode(rIndKind, rPer);
    }
    return { op, left: indicatorNode(leftKind, leftPer), right };
  }

  function setupCustomBuilder() {
    document.querySelectorAll(".custom-rule-row").forEach((row) => {
      const rightKind   = row.querySelector(".custom-right-kind");
      const rightConst  = row.querySelector(".custom-right-const");
      const rightInd    = row.querySelector(".custom-right-ind");
      const rightPeriod = row.querySelector(".custom-right-period");
      const leftKind    = row.querySelector(".custom-left-ind");
      const leftPeriod  = row.querySelector(".custom-left-period");

      function sync() {
        // RHS visibility
        const useConst = rightKind.value === "const";
        rightConst.hidden  = !useConst;
        rightInd.hidden    =  useConst;
        rightPeriod.hidden =  useConst || rightInd.value === "close";
        // LHS "close" has no period
        leftPeriod.hidden = leftKind.value === "close";
      }
      [rightKind, rightInd, leftKind].forEach((el) => el.addEventListener("change", sync));
      sync();
    });
  }

  function buildCustomSpec() {
    if (!$("customEnabled").checked) return null;
    const label = $("customLabel").value.trim() || "Custom Strategy";
    const rows = document.querySelectorAll(".custom-rule-row");
    const entry = compileRule(rows[0]);
    const exit_ = compileRule(rows[1]);
    return { label, entry, exit: exit_ };
  }

  // ─── Submit handler ───────────────────────────────────────────────
  async function runBacktest(evt) {
    evt.preventDefault();
    setError(null);

    const payload = buildPayload();
    if (!payload) return;

    document.body.classList.add("loading");
    try {
      const response = await apiPost("/api/backtest", payload);
      lastResponse = response;
      renderResults(response);
      exportBtn.disabled = false;
    } catch (e) {
      setError(`Backtest failed: ${e.message}`);
    } finally {
      document.body.classList.remove("loading");
    }
  }

  function buildPayload() {
    const selected = Array.from(
      document.querySelectorAll('input[name="strategy"]:checked')
    ).map((el) => el.value);
    const customOn = $("customEnabled").checked;

    if (selected.length === 0 && !customOn) {
      setError("Pick at least one strategy (or enable the custom one).");
      return null;
    }

    const start = $("startDate").value;
    const end   = $("endDate").value;
    if (!start || !end) { setError("Start and end dates are required."); return null; }
    if (end <= start)   { setError("End date must be after start date."); return null; }

    const short = +$("shortWindow").value;
    const long  = +$("longWindow").value;
    if (long <= short) {
      setError("MA long must be greater than MA short.");
      return null;
    }

    const customSpec = buildCustomSpec();
    const strategies = customSpec ? [...selected, "custom"] : selected;

    const payload = {
      ticker: $("ticker").value.trim().toUpperCase(),
      start_date: start,
      end_date: end,
      strategies,
      initial_capital: +$("initialCapital").value,
      params: {
        short_window: short,
        long_window:  long,
        rsi_period:     +$("rsiPeriod").value,
        rsi_oversold:   +$("rsiOversold").value,
        rsi_overbought: +$("rsiOverbought").value,
      },
      broker: {
        commission_per_trade: +$("commissionPerTrade").value,
        commission_per_share: +$("commissionPerShare").value,
        slippage_bps:         +$("slippageBps").value,
      },
    };
    if (customSpec) payload.custom = customSpec;
    return payload;
  }

  // ─── Rendering ────────────────────────────────────────────────────
  function renderResults(data) {
    emptyState.hidden = true;
    resultsEl.hidden  = false;

    renderBestBanner(data);
    renderMetricsTable(data);
    renderEquityChart(data);
    populatePriceSelector(data);
    renderPriceChart(data, data.best_strategy);
    renderTradeLog(data, data.best_strategy);
  }

  function renderBestBanner(data) {
    const best = data.results.find((r) => r.strategy === data.best_strategy);
    if (!best) { bestBanner.hidden = true; return; }
    bestBanner.hidden = false;
    bestBanner.innerHTML = `
      <span class="best-label">Best on this window:</span>
      <strong>${best.label}</strong> —
      total return ${fmtPct(best.metrics.total_return_pct)},
      max drawdown ${fmtPct(best.metrics.max_drawdown_pct)}.
      <span style="color: var(--muted); font-size: 0.8rem;">
        (Rank by total return only; consider drawdown and trade count before drawing conclusions.)
      </span>`;
  }

  function renderMetricsTable(data) {
    metricsTbody.innerHTML = "";
    data.results.forEach((r) => {
      const m = r.metrics;
      const tr = document.createElement("tr");
      if (r.strategy === data.best_strategy) tr.classList.add("best");
      tr.innerHTML = `
        <td>
          <span class="cell-color" style="background:${colorFor(r.strategy)}"></span>${r.label}
        </td>
        <td class="num ${pctClass(m.total_return_pct)}">${fmtPct(m.total_return_pct)}</td>
        <td class="num ${pctClass(m.annualized_return_pct)}">${fmtPct(m.annualized_return_pct)}</td>
        <td class="num neg">${fmtPct(m.max_drawdown_pct)}</td>
        <td class="num">${fmtNum(m.sharpe_ratio, 2)}</td>
        <td class="num">${m.win_rate_pct == null ? "—" : `${m.win_rate_pct.toFixed(1)}%`}</td>
        <td class="num">${m.num_trades}</td>
        <td class="num">${fmtMoney(m.final_value)}</td>
      `;
      metricsTbody.appendChild(tr);
    });
  }

  function destroyChart(c) { if (c) c.destroy(); }

  function renderEquityChart(data) {
    const ctx = $("equityChart").getContext("2d");
    destroyChart(equityChart);

    const datasets = data.results.map((r) => ({
      label: r.label,
      data: r.equity_curve.map((p) => ({ x: p.date, y: p.value })),
      borderColor: colorFor(r.strategy),
      backgroundColor: colorFor(r.strategy) + "22",
      borderWidth: 2,
      pointRadius: 0,
      tension: 0.05,
    }));

    equityChart = new Chart(ctx, {
      type: "line",
      data: { datasets },
      options: chartBaseOptions({
        yLabel: "Portfolio value ($)",
        yFormatter: (v) => "$" + v.toLocaleString("en-US"),
      }),
    });
  }

  function populatePriceSelector(data) {
    priceSelect.innerHTML = "";
    data.results.forEach((r) => {
      const opt = document.createElement("option");
      opt.value = r.strategy;
      opt.textContent = r.label;
      if (r.strategy === data.best_strategy) opt.selected = true;
      priceSelect.appendChild(opt);
    });
    priceSelect.onchange = () => {
      renderPriceChart(lastResponse, priceSelect.value);
      renderTradeLog(lastResponse, priceSelect.value);
    };
  }

  function renderPriceChart(data, strategyId) {
    const ctx = $("priceChart").getContext("2d");
    destroyChart(priceChart);

    const strat = data.results.find((r) => r.strategy === strategyId);
    if (!strat) return;

    const priceSeries = data.prices.map((p) => ({ x: p.date, y: p.close }));
    const buys  = strat.trades.filter((t) => t.action === "BUY")
                             .map((t) => ({ x: t.date, y: t.price }));
    const sells = strat.trades.filter((t) => t.action === "SELL")
                             .map((t) => ({ x: t.date, y: t.price }));

    const datasets = [
      {
        label: `${data.ticker} Close`,
        data: priceSeries,
        borderColor: "#c4c6cc",
        backgroundColor: "rgba(196,198,204,0.05)",
        borderWidth: 1.5,
        pointRadius: 0,
        tension: 0.05,
      },
      {
        label: "Buy",
        data: buys,
        type: "scatter",
        backgroundColor: "#2fd48f",
        borderColor: "#2fd48f",
        pointRadius: 7,
        pointStyle: "triangle",
        rotation: 0,
        showLine: false,
      },
      {
        label: "Sell",
        data: sells,
        type: "scatter",
        backgroundColor: "#ff5d6c",
        borderColor: "#ff5d6c",
        pointRadius: 7,
        pointStyle: "triangle",
        rotation: 180,
        showLine: false,
      },
    ];

    priceChart = new Chart(ctx, {
      type: "line",
      data: { datasets },
      options: chartBaseOptions({
        yLabel: "Price ($)",
        yFormatter: (v) => "$" + v.toFixed(2),
      }),
    });
  }

  function renderTradeLog(data, strategyId) {
    tradesTbody.innerHTML = "";
    const strat = data.results.find((r) => r.strategy === strategyId);
    if (!strat || strat.trades.length === 0) {
      tradesTbody.innerHTML = `<tr><td colspan="5" class="muted-cell" style="text-align:center">No trades for this strategy.</td></tr>`;
      return;
    }
    strat.trades.forEach((t) => {
      const tr = document.createElement("tr");
      const actionClass = t.action === "BUY" ? "pos" : "neg";
      tr.innerHTML = `
        <td>${t.date}</td>
        <td class="${actionClass}">${t.action}</td>
        <td class="num">${fmtMoney(t.price)}</td>
        <td class="num">${t.shares.toFixed(4)}</td>
        <td class="num">${fmtMoney(t.portfolio_value)}</td>`;
      tradesTbody.appendChild(tr);
    });
  }

  // ─── Chart defaults ───────────────────────────────────────────────
  function chartBaseOptions({ yLabel, yFormatter }) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: {
        legend: {
          labels: { color: "#e6e8ec", boxWidth: 12, boxHeight: 12, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: "#1e222b",
          titleColor: "#e6e8ec",
          bodyColor: "#c4c6cc",
          borderColor: "#262b35",
          borderWidth: 1,
          callbacks: {
            label: (ctx) => {
              const label = ctx.dataset.label || "";
              const v = ctx.parsed.y;
              return `${label}: ${yFormatter(v)}`;
            },
          },
        },
      },
      scales: {
        x: {
          type: "time",
          time: { unit: "month", tooltipFormat: "yyyy-MM-dd" },
          ticks: { color: "#8b93a1", maxRotation: 0 },
          grid:  { color: "rgba(255,255,255,0.04)" },
        },
        y: {
          title: { display: true, text: yLabel, color: "#8b93a1" },
          ticks: { color: "#8b93a1", callback: (v) => yFormatter(v) },
          grid:  { color: "rgba(255,255,255,0.04)" },
        },
      },
    };
  }

  // ─── CSV export ───────────────────────────────────────────────────
  async function exportCsv() {
    if (!lastResponse) return;
    const payload = buildPayload();
    if (!payload) return;
    try {
      const blob = await apiPost("/api/backtest/export", payload, true);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `backtest_${payload.ticker}_${payload.start_date}_${payload.end_date}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(`Export failed: ${e.message}`);
    }
  }

  // ─── Init ─────────────────────────────────────────────────────────
  function init() {
    const { start, end } = defaultDateRange();
    $("startDate").value = start;
    $("endDate").value   = end;

    form.addEventListener("submit", runBacktest);
    exportBtn.addEventListener("click", exportCsv);

    setupCustomBuilder();
    loadStrategies();
    checkApiStatus();
    setInterval(checkApiStatus, 15_000);
  }

  document.addEventListener("DOMContentLoaded", init);
})();
