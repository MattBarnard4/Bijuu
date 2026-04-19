import pandas as pd
import numpy as np 



""" 
mechanical model that combines VWAP model? 

using regime filter, mean reversion


"""

def add_ema(df: pd.DataFrame, span: int = 10) -> pd.DataFrame:
    df = df.copy()
    df[f"EMA{span}"] = df["close"].ewm(span=span, adjust=False).mean()
    return df

def add_fvg(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    bullish_fvgs = []
    bearish_fvgs = []

    for i in range(1, len(df) - 1):
        if df["high"].iloc[i - 1] < df["low"].iloc[i + 1] and df["close"].iloc[i] > df["open"].iloc[i]:
            fvg_low = df["high"].iloc[i - 1]
            fvg_high = df["low"].iloc[i + 1]
            fvg_center = (fvg_high + fvg_low) / 2
            bullish_fvgs.append((fvg_high, fvg_center, fvg_low))
        else:
            bullish_fvgs.append(None)

        if df["low"].iloc[i - 1] > df["high"].iloc[i + 1] and df["close"].iloc[i] < df["open"].iloc[i]:
            fvg_high = df["low"].iloc[i - 1]
            fvg_low = df["high"].iloc[i + 1]
            fvg_center = (fvg_high + fvg_low) / 2
            bearish_fvgs.append((fvg_high, fvg_center, fvg_low))
        else:
            bearish_fvgs.append(None)

    df["bullish_fvg"] = [None] + bullish_fvgs + [None]
    df["bearish_fvg"] = [None] + bearish_fvgs + [None]

    return df

import pandas as pd


def add_vwap(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Ensure timezone-aware datetime in New York time
    df["datetime_est"] = pd.to_datetime(df["datetime"], utc=True).dt.tz_convert("America/New_York")

    # Create session key:
    # 18:00 ET and later belongs to the next trading session
    session_date = df["datetime_est"].dt.date
    after_6pm = df["datetime_est"].dt.hour >= 18

    df["session_date"] = pd.to_datetime(session_date)
    df.loc[after_6pm, "session_date"] = df.loc[after_6pm, "session_date"] + pd.Timedelta(days=1)

    # VWAP using session reset
    typical_price = (df["high"] + df["low"] + df["close"]) / 3
    df["cum_vol"] = df.groupby("session_date")["volume"].cumsum()
    df["cum_vol_price"] = (typical_price * df["volume"]).groupby(df["session_date"]).cumsum()
    df["vwap"] = df["cum_vol_price"] / df["cum_vol"]

    return df



