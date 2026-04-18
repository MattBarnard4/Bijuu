import pandas as pd
import numpy as np 



""" 
mechanical model that combines VWAP model? 

using regime filter, mean reversion


"""

def add_ema(df):
    df = df.copy()
    df['ema_10'] = df['close'].ewm(span=10, adjust=False).mean()
    return df

def add_fvg(df):
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



def prepare_data(df):
    df = add_ema(df)
    df = add_fvg(df)
    return df
