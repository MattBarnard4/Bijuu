import pandas as pd
import numpy as np
import json
from pathlib import Path

from strategy.strategy import prepare_data, generate_signals, add_trade_levels
from analytics.metrics import build_dashboard_metrics

def add_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Basic candle features
    df["candle_body"] = (df["close"] - df["open"]).abs()
    df["candle_range"] = df["high"] - df["low"]
    df["upper_wick"] = df["high"] - df[["open", "close"]].max(axis=1)
    df["lower_wick"] = df[["open", "close"]].min(axis=1) - df["low"]

    # Returns
    df["ret_1"] = df["close"].pct_change(1)
    df["ret_3"] = df["close"].pct_change(3)
    df["ret_5"] = df["close"].pct_change(5)

    # Rolling volatility / range
    df["volatility_10"] = df["close"].pct_change().rolling(10).std()
    df["range_mean_10"] = (df["high"] - df["low"]).rolling(10).mean()

    # Momentum / trend
    df["ema_10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema_20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["dist_ema_10"] = df["close"] - df["ema_10"]
    df["dist_ema_20"] = df["close"] - df["ema_20"]
    df["ema_cross_spread"] = df["ema_10"] - df["ema_20"]

    # Volume context
    if "volume" in df.columns:
        df["vol_mean_20"] = df["volume"].rolling(20).mean()
        df["volume_ratio"] = np.where(df["vol_mean_20"] != 0, df["volume"] / df["vol_mean_20"], np.nan)
    else:
        df["volume_ratio"] = np.nan

    # Time features
    df["entry_hour"] = df["datetime"].dt.hour
    df["entry_dayofweek"] = df["datetime"].dt.dayofweek

    # Optional: cyclical hour encoding
    df["hour_sin"] = np.sin(2 * np.pi * df["entry_hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["entry_hour"] / 24)

    return df

def run_backtest(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy().reset_index(drop=True)

    trades = []
    in_trade = False
    current_trade = None

    i = 0
    while i < len(df):
        row = df.iloc[i]

        if not in_trade and row["signal"] != 0:
            direction = "LONG" if row["signal"] == 1 else "SHORT"

            entry_price = row["entry_price"]
            stop_price = row["stop_price"]
            target_price = row["target_price"]

            if pd.isna(entry_price) or pd.isna(stop_price) or pd.isna(target_price):
                i += 1
                continue

            current_trade = {
                "entry_index": i,
                "entry_time": row["datetime"],
                "side": direction,
                "entry_price": entry_price,
                "stop_price": stop_price,
                "target_price": target_price,

                # ML features known at entry
                "open_at_entry": row.get("open", np.nan),
                "high_at_entry": row.get("high", np.nan),
                "low_at_entry": row.get("low", np.nan),
                "close_at_entry": row.get("close", np.nan),

                "candle_body": row.get("candle_body", np.nan),
                "candle_range": row.get("candle_range", np.nan),
                "upper_wick": row.get("upper_wick", np.nan),
                "lower_wick": row.get("lower_wick", np.nan),

                "ret_1": row.get("ret_1", np.nan),
                "ret_3": row.get("ret_3", np.nan),
                "ret_5": row.get("ret_5", np.nan),

                "volatility_10": row.get("volatility_10", np.nan),
                "range_mean_10": row.get("range_mean_10", np.nan),

                "ema_10": row.get("ema_10", np.nan),
                "ema_20": row.get("ema_20", np.nan),
                "dist_ema_10": row.get("dist_ema_10", np.nan),
                "dist_ema_20": row.get("dist_ema_20", np.nan),
                "ema_cross_spread": row.get("ema_cross_spread", np.nan),

                "volume_ratio": row.get("volume_ratio", np.nan),

                "entry_hour": row.get("entry_hour", np.nan),
                "entry_dayofweek": row.get("entry_dayofweek", np.nan),
                "hour_sin": row.get("hour_sin", np.nan),
                "hour_cos": row.get("hour_cos", np.nan),
            }

            in_trade = True
            i += 1
            continue

        if in_trade and current_trade is not None:
            high = row["high"]
            low = row["low"]

            exit_price = None
            exit_reason = None

            if current_trade["side"] == "LONG":
                stop_hit = low <= current_trade["stop_price"]
                target_hit = high >= current_trade["target_price"]

                if stop_hit and target_hit:
                    exit_price = current_trade["stop_price"]
                    exit_reason = "stop_and_target_same_bar"
                elif stop_hit:
                    exit_price = current_trade["stop_price"]
                    exit_reason = "stop"
                elif target_hit:
                    exit_price = current_trade["target_price"]
                    exit_reason = "target"

            else:
                stop_hit = high >= current_trade["stop_price"]
                target_hit = low <= current_trade["target_price"]

                if stop_hit and target_hit:
                    exit_price = current_trade["stop_price"]
                    exit_reason = "stop_and_target_same_bar"
                elif stop_hit:
                    exit_price = current_trade["stop_price"]
                    exit_reason = "stop"
                elif target_hit:
                    exit_price = current_trade["target_price"]
                    exit_reason = "target"

            if exit_price is not None:
                entry_price = current_trade["entry_price"]
                stop_price = current_trade["stop_price"]

                if current_trade["side"] == "LONG":
                    pnl = exit_price - entry_price
                    risk = entry_price - stop_price
                else:
                    pnl = entry_price - exit_price
                    risk = stop_price - entry_price

                r_multiple = pnl / risk if risk != 0 else np.nan

                trades.append({
                    "entry_time": current_trade["entry_time"],
                    "exit_time": row["datetime"],
                    "side": current_trade["side"],
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "stop_price": current_trade["stop_price"],
                    "target_price": current_trade["target_price"],
                    "pnl": pnl,
                    "r_multiple": r_multiple,
                    "stop_size": abs(risk),
                    "exit_reason": exit_reason,
                    "bars_held": i - current_trade["entry_index"],
                    "open_at_entry": current_trade["open_at_entry"],
                    "high_at_entry": current_trade["high_at_entry"],
                    "low_at_entry": current_trade["low_at_entry"],
                    "close_at_entry": current_trade["close_at_entry"],

                    "candle_body": current_trade["candle_body"],
                    "candle_range": current_trade["candle_range"],
                    "upper_wick": current_trade["upper_wick"],
                    "lower_wick": current_trade["lower_wick"],

                    "ret_1": current_trade["ret_1"],
                    "ret_3": current_trade["ret_3"],
                    "ret_5": current_trade["ret_5"],

                    "volatility_10": current_trade["volatility_10"],
                    "range_mean_10": current_trade["range_mean_10"],

                    "ema_10": current_trade["ema_10"],
                    "ema_20": current_trade["ema_20"],
                    "dist_ema_10": current_trade["dist_ema_10"],
                    "dist_ema_20": current_trade["dist_ema_20"],
                    "ema_cross_spread": current_trade["ema_cross_spread"],

                    "volume_ratio": current_trade["volume_ratio"],

                    "entry_hour": current_trade["entry_hour"],
                    "entry_dayofweek": current_trade["entry_dayofweek"],
                    "hour_sin": current_trade["hour_sin"],
                    "hour_cos": current_trade["hour_cos"],
                })

                in_trade = False
                current_trade = None

        i += 1

    return pd.DataFrame(trades)


def build_results_df_from_trades(
    trades_df: pd.DataFrame,
    starting_capital: float = 100000
) -> pd.DataFrame:
    trades_df = trades_df.copy()

    if trades_df.empty:
        return pd.DataFrame(columns=["date", "equity", "returns", "drawdown"])

    trades_df["exit_time"] = pd.to_datetime(trades_df["exit_time"], errors="coerce")
    trades_df = trades_df.sort_values("exit_time").reset_index(drop=True)

    trades_df["cum_pnl"] = trades_df["pnl"].cumsum()
    trades_df["equity"] = starting_capital + trades_df["cum_pnl"]
    trades_df["returns"] = trades_df["equity"].pct_change().fillna(0)
    trades_df["peak"] = trades_df["equity"].cummax()
    trades_df["drawdown"] = (trades_df["equity"] - trades_df["peak"]) / trades_df["peak"]

    results_df = trades_df[["exit_time", "equity", "returns", "drawdown"]].copy()
    results_df = results_df.rename(columns={"exit_time": "date"})

    return results_df


def run_pipeline(
    csv_path: str = "data/nq_continuous_1m.csv",
    starting_capital: float = 100000
) -> dict:
    df = pd.read_csv(csv_path, parse_dates=["datetime"])

    df = prepare_data(df)
    df = generate_signals(df)
    df = add_trade_levels(df)
    df = add_ml_features(df)

    trades_df = run_backtest(df)
    results_df = build_results_df_from_trades(trades_df, starting_capital=starting_capital)
    metrics = build_dashboard_metrics(results_df, trades_df)

    return {
        "source_df": df,
        "trades_df": trades_df,
        "results_df": results_df,
        "metrics": metrics,
    }


def export_pipeline_outputs(
    output_dir: str = "exports",
    csv_path: str = "data/nq_continuous_1m.csv",
    starting_capital: float = 100000
) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    data = run_pipeline(csv_path=csv_path, starting_capital=starting_capital)

    trades_df = data["trades_df"].copy()
    results_df = data["results_df"].copy()
    metrics = data["metrics"]

    # Optional NN target
    if not trades_df.empty:
        trades_df["target"] = (pd.to_numeric(trades_df["pnl"], errors="coerce") > 0).astype(int)

    trades_df.to_csv(output_path / "trades.csv", index=False)
    results_df.to_csv(output_path / "results.csv", index=False)

    with open(output_path / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)

    print(f"Exported files to: {output_path.resolve()}")
    print(" - trades.csv")
    print(" - results.csv")
    print(" - metrics.json")


if __name__ == "__main__":
    export_pipeline_outputs()