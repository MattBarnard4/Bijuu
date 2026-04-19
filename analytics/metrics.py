from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


EST_TZ = ZoneInfo("America/New_York")


def _safe_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.mean()) if not series.empty else 0.0


def _safe_std(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.std()) if not series.empty else 0.0


def _safe_sum(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    return float(series.sum()) if not series.empty else 0.0


def _safe_pct(part: int | float, whole: int | float) -> float:
    return float(part / whole) if whole else 0.0


def _coerce_datetime(series: pd.Series, utc: bool = True) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=utc)


def prepare_results_df(results_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures results_df has:
    - date
    - returns
    - equity
    - drawdown
    """
    df = results_df.copy()

    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    if "returns" not in df.columns and "equity" in df.columns:
        df["returns"] = pd.to_numeric(df["equity"], errors="coerce").pct_change().fillna(0)

    if "drawdown" not in df.columns and "equity" in df.columns:
        equity = pd.to_numeric(df["equity"], errors="coerce")
        peak = equity.cummax()
        df["drawdown"] = (equity - peak) / peak

    return df


def prepare_trades_df(trades_df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensures trades_df has clean numeric columns and parsed datetimes.
    Expected columns when available:
    - entry_time
    - side
    - pnl
    - r_multiple
    - stop_size
    """
    df = trades_df.copy()

    numeric_cols = ["entry_price", "exit_price", "pnl", "r_multiple", "stop_size"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "entry_time" in df.columns:
        df["entry_time"] = _coerce_datetime(df["entry_time"], utc=True)

    return df


def calculate_sharpe_ratio(results_df: pd.DataFrame, periods_per_year: int = 252) -> float:
    df = prepare_results_df(results_df)
    if "returns" not in df.columns:
        return 0.0

    mean_return = _safe_mean(df["returns"])
    std_return = _safe_std(df["returns"])

    if std_return == 0:
        return 0.0

    return float((mean_return / std_return) * np.sqrt(periods_per_year))


def calculate_max_drawdown(results_df: pd.DataFrame) -> float:
    df = prepare_results_df(results_df)
    if "drawdown" not in df.columns:
        return 0.0
    return float(pd.to_numeric(df["drawdown"], errors="coerce").min())


def calculate_avg_drawdown(results_df: pd.DataFrame) -> float:
    df = prepare_results_df(results_df)
    if "drawdown" not in df.columns:
        return 0.0

    dd = pd.to_numeric(df["drawdown"], errors="coerce")
    dd = dd[dd < 0]
    return float(dd.mean()) if not dd.empty else 0.0


def calculate_recovery_time(results_df: pd.DataFrame) -> int:
    df = prepare_results_df(results_df)
    if "equity" not in df.columns:
        return 0

    equity = pd.to_numeric(df["equity"], errors="coerce").reset_index(drop=True)
    peak = equity.cummax()
    underwater = equity < peak

    recovery_lengths: list[int] = []
    in_drawdown = False
    start_idx: int | None = None

    for i, is_underwater in enumerate(underwater):
        if is_underwater and not in_drawdown:
            in_drawdown = True
            start_idx = i
        elif not is_underwater and in_drawdown:
            in_drawdown = False
            if start_idx is not None:
                recovery_lengths.append(i - start_idx)

    return int(round(np.mean(recovery_lengths))) if recovery_lengths else 0


def calculate_avg_r_per_win(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "r_multiple" not in df.columns or "pnl" not in df.columns:
        return 0.0

    wins = df[df["pnl"] > 0]
    return _safe_mean(wins["r_multiple"])


def calculate_avg_r_per_loss(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "r_multiple" not in df.columns or "pnl" not in df.columns:
        return 0.0

    losses = df[df["pnl"] < 0]
    return _safe_mean(losses["r_multiple"])


def calculate_avg_r_all(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "r_multiple" not in df.columns:
        return 0.0
    return _safe_mean(df["r_multiple"])


def calculate_rr_secured(trades_df: pd.DataFrame) -> float:
    avg_r_win = calculate_avg_r_per_win(trades_df)
    avg_r_loss = calculate_avg_r_per_loss(trades_df)

    if avg_r_loss == 0:
        return 0.0

    return float(abs(avg_r_win / avg_r_loss))


def calculate_expectancy_r(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "pnl" not in df.columns or "r_multiple" not in df.columns:
        return 0.0

    total_trades = len(df)
    if total_trades == 0:
        return 0.0

    wins = df[df["pnl"] > 0]
    losses = df[df["pnl"] < 0]

    win_rate = _safe_pct(len(wins), total_trades)
    loss_rate = _safe_pct(len(losses), total_trades)

    avg_r_win = _safe_mean(wins["r_multiple"])
    avg_r_loss = _safe_mean(losses["r_multiple"])

    return float((win_rate * avg_r_win) + (loss_rate * avg_r_loss))


def calculate_expectancy_dollar(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "pnl" not in df.columns:
        return 0.0
    return _safe_mean(df["pnl"])


def calculate_avg_stop_size(trades_df: pd.DataFrame) -> float:
    df = prepare_trades_df(trades_df)
    if "stop_size" in df.columns:
        return _safe_mean(df["stop_size"])

    if "pnl" in df.columns and "r_multiple" in df.columns:
        implied_stop = np.abs(df["pnl"] / df["r_multiple"].replace(0, np.nan))
        implied_stop = pd.Series(implied_stop).replace([np.inf, -np.inf], np.nan)
        return _safe_mean(implied_stop)

    return 0.0


def calculate_avg_win_direction(trades_df: pd.DataFrame) -> float:
    """
    Returns the percentage of winning trades that were LONG.
    """
    df = prepare_trades_df(trades_df)
    if "side" not in df.columns or "pnl" not in df.columns:
        return 0.0

    wins = df[df["pnl"] > 0]
    if wins.empty:
        return 0.0

    return float(wins["side"].astype(str).str.upper().eq("LONG").mean() * 100)


def calculate_avg_loss_direction(trades_df: pd.DataFrame) -> float:
    """
    Returns the percentage of losing trades that were LONG.
    """
    df = prepare_trades_df(trades_df)
    if "side" not in df.columns or "pnl" not in df.columns:
        return 0.0

    losses = df[df["pnl"] < 0]
    if losses.empty:
        return 0.0

    return float(losses["side"].astype(str).str.upper().eq("LONG").mean() * 100)


def calculate_risk_of_ruin(trades_df: pd.DataFrame) -> float:
    """
    Placeholder risk-of-ruin estimate using current win rate and RR profile.
    Not a full professional model, but fine for the UI stage.
    """
    df = prepare_trades_df(trades_df)
    if df.empty or "pnl" not in df.columns:
        return 0.0

    total_trades = len(df)
    wins = df[df["pnl"] > 0]
    win_rate = _safe_pct(len(wins), total_trades)
    rr_secured = calculate_rr_secured(df)

    if rr_secured <= 0 or win_rate <= 0:
        return 0.0

    ruin = ((1 - win_rate) / (1 + rr_secured)) ** 2
    ruin = max(0.0, min(1.0, ruin))
    return float(ruin * 100)


def calculate_win_loss_distribution(trades_df: pd.DataFrame) -> dict[str, int]:
    """
    Bucket R-multiples for histogram-style dashboard charts.
    """
    df = prepare_trades_df(trades_df)
    if "r_multiple" not in df.columns:
        return {
            "<-3R": 0,
            "-2:-3R": 0,
            "-1:-2R": 0,
            "0:-1R": 0,
            "0:1R": 0,
            "1:2R": 0,
            "2:3R": 0,
            ">3R": 0,
        }

    r = pd.to_numeric(df["r_multiple"], errors="coerce")

    buckets = {
        "<-3R": int((r < -3).sum()),
        "-2:-3R": int(((r >= -3) & (r < -2)).sum()),
        "-1:-2R": int(((r >= -2) & (r < -1)).sum()),
        "0:-1R": int(((r >= -1) & (r < 0)).sum()),
        "0:1R": int(((r >= 0) & (r < 1)).sum()),
        "1:2R": int(((r >= 1) & (r < 2)).sum()),
        "2:3R": int(((r >= 2) & (r < 3)).sum()),
        ">3R": int((r >= 3).sum()),
    }
    return buckets


def calculate_pnl_by_hour_est(trades_df: pd.DataFrame) -> dict[str, float]:
    """
    Groups PnL by entry hour in New York time.
    """
    df = prepare_trades_df(trades_df)
    if "entry_time" not in df.columns or "pnl" not in df.columns:
        return {}

    valid = df.dropna(subset=["entry_time"]).copy()
    if valid.empty:
        return {}

    valid["entry_time_est"] = valid["entry_time"].dt.tz_convert(EST_TZ)
    valid["hour_est"] = valid["entry_time_est"].dt.hour

    grouped = valid.groupby("hour_est")["pnl"].sum().sort_index()
    return {str(int(hour)): float(value) for hour, value in grouped.items()}


def calculate_pnl_by_day(trades_df: pd.DataFrame) -> dict[str, float]:
    """
    Groups PnL by weekday based on entry_time in EST.
    """
    df = prepare_trades_df(trades_df)
    if "entry_time" not in df.columns or "pnl" not in df.columns:
        return {}

    valid = df.dropna(subset=["entry_time"]).copy()
    if valid.empty:
        return {}

    valid["entry_time_est"] = valid["entry_time"].dt.tz_convert(EST_TZ)
    valid["weekday"] = valid["entry_time_est"].dt.day_name()

    ordered_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grouped = valid.groupby("weekday")["pnl"].sum()

    return {
        day: float(grouped.get(day, 0.0))
        for day in ordered_days
        if day in grouped.index
    }


def build_dashboard_metrics(results_df: pd.DataFrame, trades_df: pd.DataFrame) -> dict[str, Any]:
    """
    Main function to generate all dashboard metrics in one dictionary.
    """
    return {
        "sharpe_ratio": calculate_sharpe_ratio(results_df),
        "rr_secured": calculate_rr_secured(trades_df),
        "avg_stop_size": calculate_avg_stop_size(trades_df),
        "ev_r": calculate_expectancy_r(trades_df),
        "ev_dollar": calculate_expectancy_dollar(trades_df),
        "avg_r_per_win": calculate_avg_r_per_win(trades_df),
        "avg_r_per_loss": calculate_avg_r_per_loss(trades_df),
        "avg_r_all": calculate_avg_r_all(trades_df),
        "max_dd": calculate_max_drawdown(results_df),
        "avg_dd": calculate_avg_drawdown(results_df),
        "recovery_time": calculate_recovery_time(results_df),
        "avg_win_direction": calculate_avg_win_direction(trades_df),
        "avg_loss_direction": calculate_avg_loss_direction(trades_df),
        "risk_of_ruin": calculate_risk_of_ruin(trades_df),
        "win_loss_distribution": calculate_win_loss_distribution(trades_df),
        "pnl_by_hour_est": calculate_pnl_by_hour_est(trades_df),
        "pnl_by_day": calculate_pnl_by_day(trades_df),
    }