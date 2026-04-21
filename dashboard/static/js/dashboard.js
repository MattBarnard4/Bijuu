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
    ["Beat Backtest Probability", `${s.probability_beat_backtest}%`, "Chance a simulated path finishes at or above the realised backtest."],
  ];

  document.getElementById("monte-carlo-cards").innerHTML = cards
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
function baseMiniLayout() {
  return {
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: {
      color: "#f4f7ff",
      family: "Inter, Segoe UI, Arial, sans-serif"
    },
    margin: { l: 42, r: 12, t: 8, b: 34 },
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
  const distColors = charts.win_loss_distribution.values.map(v =>
    v >= 0 ? "#69e1b0" : "#ff6b81"
  );

  Plotly.newPlot(
    "winloss-chart",
    [{
      x: charts.win_loss_distribution.labels,
      y: charts.win_loss_distribution.values,
      type: "bar",
      marker: {
        color: distColors,
        line: { color: distColors, width: 1 }
      },
      hovertemplate: "%{x}<br>%{y}<extra></extra>"
    }],
    {
      ...baseMiniLayout()
    },
    { responsive: true, displayModeBar: false }
  );

  const hourColors = charts.pnl_by_hour.values.map(v =>
    v >= 0 ? "#69e1b0" : "#ff6b81"
  );

  Plotly.newPlot(
    "hour-chart",
    [{
      x: charts.pnl_by_hour.labels,
      y: charts.pnl_by_hour.values,
      type: "bar",
      marker: {
        color: hourColors,
        line: { color: hourColors, width: 1 }
      },
      hovertemplate: "%{x}:00<br>$%{y}<extra></extra>"
    }],
    {
      ...baseMiniLayout()
    },
    { responsive: true, displayModeBar: false }
  );

  const dayColors = charts.pnl_by_day.values.map(v =>
    v >= 0 ? "#69e1b0" : "#ff6b81"
  );

  Plotly.newPlot(
    "day-chart",
    [{
      x: charts.pnl_by_day.labels,
      y: charts.pnl_by_day.values,
      type: "bar",
      marker: {
        color: dayColors,
        line: { color: dayColors, width: 1 }
      },
      hovertemplate: "%{x}<br>$%{y}<extra></extra>"
    }],
    {
      ...baseMiniLayout()
    },
    { responsive: true, displayModeBar: false }
  );
}
async function initDashboard() {
  const res = await fetch("/api/dashboard-data");
  const data = await res.json();

  renderTopCharts(data.charts);   // 👈 ADD THIS BACK

  renderCards(data.metrics);
  renderMonteCarloCards(data.monte_carlo);
  renderSummary(data.metrics);
  renderTrades(data.trades);
  renderMonteCarloChart(data.monte_carlo);
  renderChart(data.equity_curve);
}

initDashboard();