function metricColorClass(label, value) {
  const negativeLabels = ["Max DD", "Avg R Per Loss", "Risk of Ruin"];
  const positiveLabels = ["Sharpe Ratio", "RR Secured", "Avg R Per Win"];

  if (negativeLabels.includes(label)) return "negative";
  if (positiveLabels.includes(label)) return "positive";
  if (label === "EV") return "gold";
  if (label === "Avg Stop Size") return "accent";
  if (label === "Avg Drawdown") return "warning";
  return "";
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
    ["Avg Stop Size", `$${metrics.avg_stop_size}`, "Average dollar distance from entry to stop-loss."],
    ["EV", `${metrics.ev}R`, "Expected value per trade in R-multiple terms."],
    ["Avg R Per Win", metrics.avg_r_per_win, "Average R-multiple achieved on winning trades."],
    ["Avg R Per Loss", metrics.avg_r_per_loss, "Average R-multiple taken on losing trades."]
  ];

  const risk = [
    ["Max DD", `${metrics.max_dd}%`, "Largest peak-to-trough drawdown across the test window."],
    ["Avg Win Direction", `${metrics.avg_win_direction}%`, "Percent of winning trades that were LONG."],
    ["Avg Loss Direction", `${metrics.avg_loss_direction}%`, "Percent of losing trades that were LONG."],
    ["Risk of Ruin", `${metrics.risk_of_ruin}%`, "Placeholder estimate using current win-rate / R profile."],
    ["Avg Drawdown", `${metrics.avg_dd}%`, "Mean depth of drawdown periods."],
    ["Monte Carlo", metrics.monte_carlo, "Not wired yet. Reserved for future simulation output."]
  ];

  document.getElementById("performance-cards").innerHTML = performance
    .map(([l, v, d]) => createCard(l, v, d))
    .join("");

  document.getElementById("risk-cards").innerHTML = risk
    .map(([l, v, d]) => createCard(l, v, d))
    .join("");
}

function renderSummary(metrics) {
  document.getElementById("run-summary").textContent =
`Trades: ${metrics.total_trades}
Sharpe: ${metrics.sharpe_ratio}
EV: ${metrics.ev}R
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

function renderChart(curve) {
  const equityTrace = {
    x: curve.dates,
    y: curve.equity,
    type: "scatter",
    mode: "lines",
    name: "Equity",
    line: { color: "#7c83ff", width: 2.5 }
  };

  const ddTrace = {
    x: curve.dates,
    y: curve.drawdown,
    type: "scatter",
    mode: "lines",
    name: "Drawdown %",
    line: { color: "#ff6b81", width: 1.8 },
    fill: "tozeroy",
    yaxis: "y2"
  };

  const layout = {
    paper_bgcolor: "#0c1020",
    plot_bgcolor: "#0c1020",
    font: { color: "#f4f7ff" },
    margin: { l: 45, r: 25, t: 20, b: 45 },
    xaxis: { gridcolor: "#141a31", zerolinecolor: "#141a31" },
    yaxis: { title: "Equity", gridcolor: "#141a31", zerolinecolor: "#141a31" },
    yaxis2: {
      title: "Drawdown %",
      overlaying: "y",
      side: "right",
      gridcolor: "#141a31",
      zerolinecolor: "#141a31"
    },
    legend: { orientation: "h", y: 1.08, x: 0 }
  };

  Plotly.newPlot("equity-chart", [equityTrace, ddTrace], layout, { responsive: true });
}

async function initDashboard() {
  const res = await fetch("/api/dashboard-data");
  const data = await res.json();

  renderCards(data.metrics);
  renderSummary(data.metrics);
  renderTrades(data.trades);
  renderChart(data.equity_curve);
}

initDashboard();