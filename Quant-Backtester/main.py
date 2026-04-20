import pandas as pd
import numpy as np

from strategy.strategy import prepare_data, generate_signals, add_trade_levels
from analytics.metrics import build_dashboard_metrics


df = pd.read_csv("data/nqm6_clean_1m.csv", parse_dates=["datetime"])


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


df = prepare_data(df)
df = generate_signals(df)
df = add_trade_levels(df)

trades_df = run_backtest(df)
results_df = build_results_df_from_trades(trades_df, starting_capital=100000)

metrics = build_dashboard_metrics(results_df, trades_df)

print(trades_df.head())
print(results_df.head())
print(metrics)