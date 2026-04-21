let dashboardData = null;
let monteCarloRendered = false;

function metricColorClass(label, value) {
  const negativeLabels = ["Max DD", "Avg R Per Loss", "Risk of Ruin"];
  const positiveLabels = ["Sharpe Ratio", "RR Secured", "Avg R Per Win"];

  if (negativeLabels.includes(label)) return "negative";
  if (positiveLabels.includes(label)) return "positive";
  if (label === "EV") return "gold";
  if (label === "Avg Stop Size") return "accent";
  if (label === "Avg Drawdown") return "warning";

  return "default"; // 👈 ADD THIS
}

function createCard(label, value, desc) {
  const cls = metricColorClass(label, value);
  return `
    <div class="card">
      <div class="card-label">${label}</div>
      <div class="card-value ${cls}">${value}</div>
      <div class="card-desc">${desc}</div>
    </div>
  `;
}

function renderCards(metrics) {
  const performance = [
    ["Sharpe Ratio", metrics.sharpe_ratio, "Annualised excess return per unit of total volatility."],
    ["RR Secured", metrics.rr_secured, "Average reward-to-risk ratio across the strategy profile."],
    ["Avg Stop Size", `$${Number(metrics.avg_stop_size).toFixed(2)}`, "Average dollar distance from entry to stop-loss."],
    ["EV", metrics.ev != null ? `${metrics.ev}R` : "N/A", "Expected value per trade in R-multiple terms."],
    ["Avg R Per Win", metrics.avg_r_per_win, "Average R-multiple achieved on winning trades."],
    ["Avg R Per Loss", metrics.avg_r_per_loss, "Average R-multiple taken on losing trades."]
  ];

  const risk = [
    ["Max DD", `${metrics.max_dd}%`, "Largest peak-to-trough drawdown across the test window."],
    ["Avg Win Direction", `${metrics.avg_win_direction}%`, "Percent of winning trades that were LONG."],
    ["Avg Loss Direction", `${metrics.avg_loss_direction}%`, "Percent of losing trades that were LONG."],
    ["Risk of Ruin", `${metrics.risk_of_ruin}%`, "Placeholder estimate using current win-rate / R profile."],
    ["Avg Drawdown", `${metrics.avg_dd}%`, "Mean depth of drawdown periods."],
    ["Monte Carlo", "Live", "Bootstrap simulations based on historical trade outcomes."]
  ];

  document.getElementById("performance-cards").innerHTML = performance
    .map(([l, v, d]) => createCard(l, v, d))
    .join("");

  document.getElementById("risk-cards").innerHTML = risk
    .map(([l, v, d]) => createCard(l, v, d))
    .join("");
}

function renderMonteCarloCards(mc) {
  const s = mc.summary;

  const cards = [
    ["Profit Probability", `${s.profit_probability}%`, "Percent of simulations finishing with positive cumulative P&L."],
    ["Median Ending P&L", `$${s.median_ending_pnl}`, "Middle simulated ending cumulative P&L outcome."],
    ["5th % Ending P&L", `$${s.p05_ending_pnl}`, "Conservative downside ending P&L estimate."],
    ["95th % Ending P&L", `$${s.p95_ending_pnl}`, "Upper-end ending P&L estimate from the simulation set."],
    ["95th % Max Drawdown", `$${s.p95_max_drawdown}`, "Severe but plausible drawdown level across simulations."],
    ["Median Losing Streak", `${s.median_longest_losing_streak}`, "Median longest consecutive losing run across paths."],
    ["Beat Backtest Probability", `${s.probability_beat_backtest}%`, "Chance a simulated path finishes at or above the realised backtest."]
  ];

  document.getElementById("monte-carlo-cards").innerHTML = cards
    .map(([l, v, d]) => createCard(l, v, d))
    .join("");
}

function renderSummary(metrics) {
  document.getElementById("run-summary").textContent =
`Trades: ${metrics.total_trades}
Sharpe: ${metrics.sharpe_ratio}
EV: ${metrics.ev != null ? `${metrics.ev}R` : "N/A"}
RR Secured: ${metrics.rr_secured}
Max DD: ${metrics.max_dd}%
Avg Drawdown: ${metrics.avg_dd}%
Risk of Ruin: ${metrics.risk_of_ruin}%
Recovery Time: ${metrics.recovery_time} days

This is currently a frontend shell using placeholder API data.`;
}

function renderTrades(trades) {
  const body = document.getElementById("trades-body");
  body.innerHTML = trades.map(t => `
    <tr>
      <td>${String(t.entry_time).slice(0, 19)}</td>
      <td>${t.side}</td>
      <td>${Number(t.entry_price).toFixed(2)}</td>
      <td>${Number(t.exit_price).toFixed(2)}</td>
      <td class="${t.pnl >= 0 ? "positive" : "negative"}">${Number(t.pnl).toFixed(2)}</td>
      <td class="${t.r_multiple >= 0 ? "positive" : "negative"}">${Number(t.r_multiple).toFixed(2)}</td>
    </tr>
  `).join("");
}

function baseMiniLayout() {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      color: "#f4f7ff",
      family: "Inter, Segoe UI, Arial, sans-serif"
    },
    margin: { l: 40, r: 12, t: 6, b: 30 },
    xaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 },
      fixedrange: true
    },
    yaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 },
      fixedrange: true
    },
    bargap: 0.28,
    showlegend: false
  };
}

function renderTopCharts(charts) {
  if (!charts) return;

  const dist = charts.win_loss_distribution;
  const hour = charts.pnl_by_hour;
  const day = charts.pnl_by_day;

  if (!dist || !hour || !day) return;

  const miniLayout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      color: "#f4f7ff",
      family: "Inter, Segoe UI, Arial, sans-serif"
    },
    margin: { l: 36, r: 10, t: 6, b: 30 },
    xaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 10 },
      fixedrange: true
    },
    yaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 10 },
      fixedrange: true
    },
    bargap: 0.28,
    showlegend: false
  };

  Plotly.newPlot(
    "winloss-chart",
    [{
      x: dist.labels,
      y: dist.values,
      type: "bar",
      marker: {
        color: dist.values.map(v => v >= 0 ? "#69e1b0" : "#ff6b81")
      },
      hovertemplate: "%{x}<br>%{y}<extra></extra>"
    }],
    miniLayout,
    { responsive: true, displayModeBar: false }
  );

  Plotly.newPlot(
    "hour-chart",
    [{
      x: hour.labels,
      y: hour.values,
      type: "bar",
      marker: {
        color: hour.values.map(v => v >= 0 ? "#69e1b0" : "#ff6b81")
      },
      hovertemplate: "%{x}:00<br>$%{y:,.2f}<extra></extra>"
    }],
    miniLayout,
    { responsive: true, displayModeBar: false }
  );

  Plotly.newPlot(
    "day-chart",
    [{
      x: day.labels,
      y: day.values,
      type: "bar",
      marker: {
        color: day.values.map(v => v >= 0 ? "#69e1b0" : "#ff6b81")
      },
      hovertemplate: "%{x}<br>$%{y:,.2f}<extra></extra>"
    }],
    miniLayout,
    { responsive: true, displayModeBar: false }
  );
}

function renderMonteCarloChart(mc) {
  const chart = mc.chart;

  const sampleTraces = chart.sample_paths.map(path => ({
    x: chart.x,
    y: path,
    type: "scatter",
    mode: "lines",
    line: {
      color: "rgba(124, 131, 255, 0.12)",
      width: 1
    },
    hoverinfo: "skip",
    showlegend: false
  }));

  const bandUpper = {
    x: chart.x,
    y: chart.p95,
    type: "scatter",
    mode: "lines",
    line: { color: "rgba(105, 225, 176, 0.0)", width: 0 },
    hoverinfo: "skip",
    showlegend: false
  };

  const bandLower = {
    x: chart.x,
    y: chart.p05,
    type: "scatter",
    mode: "lines",
    fill: "tonexty",
    fillcolor: "rgba(124, 131, 255, 0.16)",
    line: { color: "rgba(105, 225, 176, 0.0)", width: 0 },
    name: "5th-95th Band"
  };

  const medianTrace = {
    x: chart.x,
    y: chart.p50,
    type: "scatter",
    mode: "lines",
    name: "Median Path",
    line: { color: "#7c83ff", width: 3 }
  };

  const layout = {
    paper_bgcolor: "#0c1020",
    plot_bgcolor: "#0c1020",
    font: { color: "#f4f7ff" },
    margin: { l: 45, r: 25, t: 10, b: 45 },
    xaxis: {
      title: "Trade Number",
      gridcolor: "#141a31",
      zerolinecolor: "#141a31"
    },
    yaxis: {
      title: "Cumulative P&L",
      gridcolor: "#141a31",
      zerolinecolor: "#141a31"
    },
    legend: { orientation: "h", y: 1.08, x: 0 }
  };

  Plotly.newPlot(
    "monte-carlo-chart",
    [...sampleTraces, bandUpper, bandLower, medianTrace],
    layout,
    { responsive: true, displayModeBar: false }
  );
}

function renderEquityChart(curve) {
  const equityTrace = {
    x: curve.dates,
    y: curve.equity,
    type: "scatter",
    mode: "lines",
    line: { color: "#7c83ff", width: 2.2 },
    fill: "tozeroy",
    fillcolor: "rgba(124, 131, 255, 0.08)",
    hovertemplate: "%{x}<br>$%{y:,.2f}<extra></extra>"
  };

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#f4f7ff" },
    margin: { l: 42, r: 14, t: 10, b: 34 },
    xaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 }
    },
    yaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 }
    },
    showlegend: false
  };

  Plotly.newPlot("equity-chart", [equityTrace], layout, {
    responsive: true,
    displayModeBar: false
  });
}

function renderDrawdownChart(curve) {
  const drawdownAbs = curve.drawdown.map(v => Math.abs(Number(v)));

  const ddTrace = {
    x: curve.dates,
    y: drawdownAbs,
    type: "scatter",
    mode: "lines",
    line: { color: "#ff4d4f", width: 1.8 },
    fill: "tozeroy",
    fillcolor: "rgba(255, 77, 79, 0.12)",
    hovertemplate: "%{x}<br>%{y:.2f}%<extra></extra>"
  };

  const layout = {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { color: "#f4f7ff" },
    margin: { l: 42, r: 14, t: 10, b: 34 },
    xaxis: {
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 }
    },
    yaxis: {
      autorange: "reversed",
      range: [Math.max(...drawdownAbs) * 1.2, 0],
      gridcolor: "#141a31",
      zerolinecolor: "#141a31",
      tickfont: { color: "#7d88ad", size: 11 }
    },
    showlegend: false
  };

  Plotly.newPlot("drawdown-chart", [ddTrace], layout, {
    responsive: true,
    displayModeBar: false
  });
}

function resizePlot(id) {
  const el = document.getElementById(id);
  if (el && el.data) {
    Plotly.Plots.resize(el);
  }
}

function switchTab(targetId) {
  document.querySelectorAll(".tab-view").forEach(view => {
    view.classList.add("hidden");
  });

  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.classList.remove("active");
  });

  document.getElementById(targetId).classList.remove("hidden");
  document.querySelector(`.nav-tab[data-tab="${targetId}"]`).classList.add("active");

  if (targetId === "monte-carlo-view" && dashboardData && !monteCarloRendered) {
    renderMonteCarloCards(dashboardData.monte_carlo);
    renderMonteCarloChart(dashboardData.monte_carlo);
    monteCarloRendered = true;
  }

setTimeout(() => {
  Plotly.Plots.resize(document.getElementById("equity-chart"));
  Plotly.Plots.resize(document.getElementById("drawdown-chart"));
  Plotly.Plots.resize(document.getElementById("winloss-chart"));
  Plotly.Plots.resize(document.getElementById("hour-chart"));
  Plotly.Plots.resize(document.getElementById("day-chart"));
}, 120);
}

function initNav() {
  document.querySelectorAll(".nav-tab").forEach(tab => {
    tab.addEventListener("click", () => {
      switchTab(tab.dataset.tab);
    });
  });
}

async function initDashboard() {
  initNav();

  const res = await fetch("/api/dashboard-data");
  const data = await res.json();
  dashboardData = data;

  if (data.charts) renderTopCharts(data.charts);

  if (data.metrics) {
    renderCards(data.metrics);
    renderSummary(data.metrics);
  }

  if (data.trades) renderTrades(data.trades);

  if (data.equity_curve) {
    renderEquityChart(data.equity_curve);
    renderDrawdownChart(data.equity_curve);
  }
}

initDashboard();