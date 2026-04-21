from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))

from main import run_pipeline
from flask import Flask, jsonify, render_template
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


def longest_losing_streak(pnl_row):
    longest = 0
    current = 0
    for v in pnl_row:
        if v < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def run_monte_carlo(trades_df, n_sims=1000, sample_paths=35):
    pnl = pd.to_numeric(trades_df["pnl"], errors="coerce").dropna().to_numpy(dtype=float)

    if pnl.size == 0:
        return {
            "summary": {
                "profit_probability": 0,
                "median_ending_pnl": 0,
                "p05_ending_pnl": 0,
                "p95_ending_pnl": 0,
                "p95_max_drawdown": 0,
                "median_longest_losing_streak": 0,
                "probability_beat_backtest": 0,
            },
            "chart": {
                "x": [],
                "p05": [],
                "p50": [],
                "p95": [],
                "sample_paths": [],
            },
        }

    rng = np.random.default_rng(42)
    n_trades = pnl.size

    # bootstrap trades with replacement
    sims = rng.choice(pnl, size=(n_sims, n_trades), replace=True)

    # cumulative pnl paths
    equity_paths = sims.cumsum(axis=1)

    # absolute drawdown in $
    running_max = np.maximum.accumulate(equity_paths, axis=1)
    drawdowns = running_max - equity_paths
    max_drawdowns = drawdowns.max(axis=1)

    ending_pnl = equity_paths[:, -1]
    realized_ending_pnl = float(pnl.cumsum()[-1])

    losing_streaks = np.array([longest_losing_streak(row) for row in sims])

    p05_curve = np.percentile(equity_paths, 5, axis=0)
    p50_curve = np.percentile(equity_paths, 50, axis=0)
    p95_curve = np.percentile(equity_paths, 95, axis=0)

    sample_idx = rng.choice(n_sims, size=min(sample_paths, n_sims), replace=False)
    sampled_paths = equity_paths[sample_idx]

    return {
        "summary": {
            "profit_probability": round(float((ending_pnl > 0).mean() * 100), 1),
            "median_ending_pnl": round(float(np.median(ending_pnl)), 2),
            "p05_ending_pnl": round(float(np.percentile(ending_pnl, 5)), 2),
            "p95_ending_pnl": round(float(np.percentile(ending_pnl, 95)), 2),
            "p95_max_drawdown": round(float(np.percentile(max_drawdowns, 95)), 2),
            "median_longest_losing_streak": int(np.median(losing_streaks)),
            "probability_beat_backtest": round(float((ending_pnl >= realized_ending_pnl).mean() * 100), 1),
        },
        "chart": {
            "x": list(range(1, n_trades + 1)),
            "p05": np.round(p05_curve, 2).tolist(),
            "p50": np.round(p50_curve, 2).tolist(),
            "p95": np.round(p95_curve, 2).tolist(),
            "sample_paths": np.round(sampled_paths, 2).tolist(),
        },
    }

def build_chart_data(trades_df: pd.DataFrame):
    df = trades_df.copy()

    df["entry_time"] = pd.to_datetime(df["entry_time"], utc=True, errors="coerce")
    df["pnl"] = pd.to_numeric(df["pnl"], errors="coerce").fillna(0)
    df["r_multiple"] = pd.to_numeric(df["r_multiple"], errors="coerce").fillna(0)

    entry_est = df["entry_time"].dt.tz_convert("America/New_York")
    df["entry_hour_est"] = entry_est.dt.hour
    df["entry_day"] = entry_est.dt.day_name()

    # Win/loss distribution by R bucket
    bucket_labels = ["<-3R", "-2:-3", "-1:-2", "0:-1", "0:1", "1:2", "2:3", ">3R"]

    bucket_values = [
        int((df["r_multiple"] < -3).sum()),
        int(((df["r_multiple"] >= -3) & (df["r_multiple"] < -2)).sum()),
        int(((df["r_multiple"] >= -2) & (df["r_multiple"] < -1)).sum()),
        int(((df["r_multiple"] >= -1) & (df["r_multiple"] < 0)).sum()),
        int(((df["r_multiple"] >= 0) & (df["r_multiple"] < 1)).sum()),
        int(((df["r_multiple"] >= 1) & (df["r_multiple"] < 2)).sum()),
        int(((df["r_multiple"] >= 2) & (df["r_multiple"] < 3)).sum()),
        int((df["r_multiple"] >= 3).sum()),
    ]

    signed_bucket_values = [
        -bucket_values[0],
        -bucket_values[1],
        -bucket_values[2],
        -bucket_values[3],
         bucket_values[4],
         bucket_values[5],
         bucket_values[6],
         bucket_values[7],
    ]

    # PnL by hour
    pnl_by_hour = (
        df.groupby("entry_hour_est")["pnl"]
        .sum()
        .reindex(range(24), fill_value=0)
    )

    # PnL by day
    ordered_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    pnl_by_day = (
        df.groupby("entry_day")["pnl"]
        .sum()
        .reindex(ordered_days, fill_value=0)
    )

    return {
        "win_loss_distribution": {
            "labels": bucket_labels,
            "values": signed_bucket_values,
        },
        "pnl_by_hour": {
            "labels": [str(h) for h in range(24)],
            "values": [round(float(v), 2) for v in pnl_by_hour.tolist()],
        },
        "pnl_by_day": {
            "labels": ["Mon", "Tue", "Wed", "Thu", "Fri"],
            "values": [round(float(v), 2) for v in pnl_by_day.tolist()],
        },
    }

@app.route("/api/dashboard-data")
def dashboard_data():
    data = run_pipeline()

    trades_df = data["trades_df"].copy()
    results_df = data["results_df"].copy()
    metrics = data["metrics"]

    monte_carlo = run_monte_carlo(trades_df)
    charts = build_chart_data(trades_df)

    return jsonify(
        {
            "metrics": metrics,
            "charts": charts,
            "monte_carlo": monte_carlo,
            "equity_curve": {
                "dates": results_df["date"].astype(str).tolist(),
                "equity": results_df["equity"].round(2).tolist(),
                "drawdown": (results_df["drawdown"] * 100).round(2).tolist(),
            },
            "trades": trades_df.tail(25).copy().assign(
                entry_time=lambda x: x["entry_time"].astype(str),
                exit_time=lambda x: x["exit_time"].astype(str),
            ).to_dict(orient="records"),
        }
    )


if __name__ == "__main__":
    import threading
    import webbrowser

    def open_browser():
        webbrowser.open("http://127.0.0.1:5000")

    threading.Timer(1, open_browser).start()
    app.run(debug=True, use_reloader=False)