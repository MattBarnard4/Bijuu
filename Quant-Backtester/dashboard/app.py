from flask import Flask, jsonify, render_template
import numpy as np
import pandas as pd
import webbrowser
import threading
import os

app = Flask(__name__, template_folder="templates", static_folder="static")

def open_browser():
    webbrowser.open("http://127.0.0.1:5000")

def load_demo_data():
    np.random.seed(42)

    periods = 260
    dates = pd.date_range("2025-01-01", periods=periods, freq="D")
    returns = np.random.normal(0.0010, 0.0115, periods)
    equity = 100000 * (1 + returns).cumprod()
    peak = pd.Series(equity).cummax()
    drawdown = (pd.Series(equity) - peak) / peak

    results_df = pd.DataFrame(
        {
            "date": dates.astype(str),
            "returns": returns,
            "equity": equity,
            "drawdown": drawdown,
        }
    )

    n = 180
    side = np.random.choice(["LONG", "SHORT"], size=n, p=[0.58, 0.42])
    r_multiple = np.round(np.random.normal(0.32, 1.15, size=n), 2)
    pnl = np.round(r_multiple * np.random.uniform(120, 280, size=n), 2)
    stop_size = np.round(np.random.uniform(120, 320, size=n), 2)

    trades_df = pd.DataFrame(
        {
            "entry_time": pd.date_range("2025-02-01", periods=n, freq="12H").astype(str),
            "side": side,
            "entry_price": np.round(np.random.uniform(18000, 21000, size=n), 2),
            "exit_price": np.round(np.random.uniform(18000, 21000, size=n), 2),
            "pnl": pnl,
            "r_multiple": r_multiple,
            "stop_size": stop_size,
        }
    )

    return results_df, trades_df


def estimate_recovery_days(df: pd.DataFrame) -> int:
    equity = df["equity"].reset_index(drop=True)
    peak = equity.cummax()
    dd = equity - peak

    recoveries = []
    in_dd = False
    start_idx = None

    for i in range(len(dd)):
        if dd.iloc[i] < 0 and not in_dd:
            in_dd = True
            start_idx = i
        elif dd.iloc[i] >= 0 and in_dd:
            in_dd = False
            if start_idx is not None:
                recoveries.append(i - start_idx)

    return int(np.mean(recoveries)) if recoveries else 0


def build_metrics(results_df: pd.DataFrame, trades_df: pd.DataFrame) -> dict:
    r = results_df.copy()
    t = trades_df.copy()

    total_trades = len(t)
    wins = t[t["pnl"] > 0]
    losses = t[t["pnl"] < 0]

    win_rate = len(wins) / total_trades if total_trades else 0
    loss_rate = len(losses) / total_trades if total_trades else 0

    mean_return = r["returns"].mean()
    std_return = r["returns"].std()
    sharpe = (mean_return / std_return) * np.sqrt(252) if std_return != 0 else 0

    max_dd = float(r["drawdown"].min())
    avg_dd = float(r.loc[r["drawdown"] < 0, "drawdown"].mean()) if (r["drawdown"] < 0).any() else 0

    avg_r_win = float(wins["r_multiple"].mean()) if not wins.empty else 0
    avg_r_loss = float(losses["r_multiple"].mean()) if not losses.empty else 0
    rr_secured = abs(avg_r_win / avg_r_loss) if avg_r_loss != 0 else 0
    ev = (win_rate * avg_r_win) + (loss_rate * avg_r_loss)

    avg_stop_size = float(t["stop_size"].mean()) if total_trades else 0
    avg_win_direction = float(wins["side"].eq("LONG").mean() * 100) if not wins.empty else 0
    avg_loss_direction = float(losses["side"].eq("LONG").mean() * 100) if not losses.empty else 0

    risk_of_ruin = max(0.0, min(100.0, (((1 - win_rate) / (1 + rr_secured)) ** 2) * 100)) if rr_secured > 0 and win_rate > 0 else 0.0

    return {
        "sharpe_ratio": round(sharpe, 2),
        "rr_secured": round(rr_secured, 2),
        "avg_stop_size": round(avg_stop_size, 0),
        "ev": round(ev, 2),
        "avg_r_per_win": round(avg_r_win, 2),
        "avg_r_per_loss": round(avg_r_loss, 2),
        "max_dd": round(max_dd * 100, 1),
        "avg_dd": round(avg_dd * 100, 1),
        "avg_win_direction": round(avg_win_direction, 1),
        "avg_loss_direction": round(avg_loss_direction, 1),
        "risk_of_ruin": round(risk_of_ruin, 1),
        "recovery_time": estimate_recovery_days(r),
        "total_trades": total_trades,
        "monte_carlo": "Coming soon",
    }


@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard-data")
def dashboard_data():
    results_df, trades_df = load_demo_data()
    metrics = build_metrics(results_df, trades_df)

    return jsonify(
        {
            "metrics": metrics,
            "equity_curve": {
                "dates": results_df["date"].tolist(),
                "equity": results_df["equity"].round(2).tolist(),
                "drawdown": (results_df["drawdown"] * 100).round(2).tolist(),
            },
            "trades": trades_df.tail(20).to_dict(orient="records"),
        }
    )


if __name__ == "__main__":
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Timer(1, open_browser).start()

    app.run(debug=True)