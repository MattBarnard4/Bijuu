from pathlib import Path
import sys
sys.path.append(str(Path(__file__).resolve().parents[1]))
from main import run_pipeline
from flask import Flask, jsonify, render_template

BASE_DIR = Path(__file__).resolve().parent
app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)



@app.route("/")
def dashboard():
    return render_template("dashboard.html")


@app.route("/api/dashboard-data")
def dashboard_data():
    data = run_pipeline()

    trades_df = data["trades_df"].copy()
    results_df = data["results_df"].copy()
    metrics = data["metrics"]

    return jsonify(
        {
            "metrics": metrics,
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