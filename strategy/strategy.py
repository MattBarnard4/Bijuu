import pandas as pd
from strategy.concepts import add_ema, add_fvg, add_vwap
import numpy as np


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    df = add_ema(df, 10)
    df = add_fvg(df)
    df = add_vwap(df)
    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["long_signal"] = False
    df["short_signal"] = False
    df["signal"] = 0

    long_condition = (
        (df["close"] > df["EMA10"]) &
        (df["close"] < df["vwap"]) &
        (df["bullish_fvg"].notna())
    )

    short_condition = (
        (df["close"] < df["EMA10"]) &
        (df["close"] > df["vwap"]) &
        (df["bearish_fvg"].notna())
    )

    df.loc[long_condition, "long_signal"] = True
    df.loc[short_condition, "short_signal"] = True
    df.loc[long_condition, "signal"] = 1
    df.loc[short_condition, "signal"] = -1

    return df

def add_trade_levels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    df["entry_price"] = np.nan
    df["stop_price"] = np.nan
    df["target_price"] = np.nan

    # long levels
    long_mask = df["signal"] == 1
    df.loc[long_mask, "entry_price"] = df.loc[long_mask, "close"]
    df.loc[long_mask, "stop_price"] = df.loc[long_mask, "low"]
    df.loc[long_mask, "target_price"] = (
        df.loc[long_mask, "close"] +
        2 * (df.loc[long_mask, "close"] - df.loc[long_mask, "low"])
    )

    # short levels
    short_mask = df["signal"] == -1
    df.loc[short_mask, "entry_price"] = df.loc[short_mask, "close"]
    df.loc[short_mask, "stop_price"] = df.loc[short_mask, "high"]
    df.loc[short_mask, "target_price"] = (
        df.loc[short_mask, "close"] -
        2 * (df.loc[short_mask, "high"] - df.loc[short_mask, "close"])
    )

    return df