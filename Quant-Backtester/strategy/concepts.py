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

def add_session_filter(
    df: pd.DataFrame,
    session: str = "asia",
) -> pd.DataFrame:
    df = df.copy()

    # assume datetime is already in New York time
    df["datetime"] = pd.to_datetime(df["datetime"])

    df["hour"] = df["datetime"].dt.hour
    df["minute"] = df["datetime"].dt.minute

    # session definitions
    df["asia_session"] = (df["hour"] >= 8) & (df["hour"] < 17)
    df["london_session"] = (df["hour"] >= 2) & (df["hour"] < 8)

    if session.lower() == "asia":
        df["in_session"] = df["asia_session"]
    elif session.lower() == "london":
        df["in_session"] = df["london_session"]
    else:
        raise ValueError("session must be either 'asia' or 'london'")

    return df

def add_macro_protected_highs_lows(
    df: pd.DataFrame,
    pivot_len: int = 2,
) -> pd.DataFrame:
    df = df.copy()

    # assume datetime is already in New York time
    df["datetime"] = pd.to_datetime(df["datetime"])

    # add hour/minute if they do not already exist
    if "hour" not in df.columns:
        df["hour"] = df["datetime"].dt.hour
    if "minute" not in df.columns:
        df["minute"] = df["datetime"].dt.minute

    # macro windows:
    # xx:45 - xx:59
    # xx:00 - xx:15
    # xx:27 - xx:33
    df["in_macro"] = (
        ((df["minute"] >= 45) & (df["minute"] <= 59)) |
        ((df["minute"] >= 0) & (df["minute"] <= 15)) |
        ((df["minute"] >= 27) & (df["minute"] <= 33))
    )

    n = len(df)

    protected_high = np.full(n, np.nan)
    protected_low = np.full(n, np.nan)

    protected_high_in_macro = np.full(n, False)
    protected_low_in_macro = np.full(n, False)

    for i in range(pivot_len, n - pivot_len):
        current_high = df["high"].iloc[i]
        current_low = df["low"].iloc[i]

        left_highs = df["high"].iloc[i - pivot_len:i]
        right_highs = df["high"].iloc[i + 1:i + 1 + pivot_len]

        left_lows = df["low"].iloc[i - pivot_len:i]
        right_lows = df["low"].iloc[i + 1:i + 1 + pivot_len]

        is_pivot_high = (current_high > left_highs.max()) and (current_high >= right_highs.max())
        is_pivot_low = (current_low < left_lows.min()) and (current_low <= right_lows.min())

        if is_pivot_high:
            protected_high[i] = current_high
            protected_high_in_macro[i] = bool(df["in_macro"].iloc[i])

        if is_pivot_low:
            protected_low[i] = current_low
            protected_low_in_macro[i] = bool(df["in_macro"].iloc[i])

    df["protected_high"] = protected_high
    df["protected_low"] = protected_low

    df["protected_high_in_macro"] = protected_high_in_macro
    df["protected_low_in_macro"] = protected_low_in_macro

    return df

def add_dtc(
    df: pd.DataFrame,
    ema_span: int = 10,
) -> pd.DataFrame:
    df = df.copy()

    ema_col = f"EMA{ema_span}"

    # if the EMA is not already in the dataframe, create it
    if ema_col not in df.columns:
        df[ema_col] = df["close"].ewm(span=ema_span, adjust=False).mean()

    # bullish DTC = close moves from at/below EMA to above EMA
    df["bullish_dtc"] = (
        (df["close"].shift(1) <= df[ema_col].shift(1)) &
        (df["close"] > df[ema_col])
    )

    # bearish DTC = close moves from at/above EMA to below EMA
    df["bearish_dtc"] = (
        (df["close"].shift(1) >= df[ema_col].shift(1)) &
        (df["close"] < df[ema_col])
    )

    # optional single direction column
    df["dtc_direction"] = np.where(
        df["bullish_dtc"],
        1,
        np.where(df["bearish_dtc"], -1, 0)
    )

    return df

def add_lvn(
    df: pd.DataFrame,
    range_mask: pd.Series,
    tick_size: float = 0.25,
    min_price: float | None = None,
    max_price: float | None = None,
) -> pd.DataFrame:
    df = df.copy()

    required_cols = {"high", "low", "volume"}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if len(range_mask) != len(df):
        raise ValueError("range_mask must be the same length as df")

    range_mask = range_mask.fillna(False).astype(bool)

    selected = df.loc[range_mask, ["high", "low", "volume"]].copy()

    if selected.empty:
        df["lvn_price"] = np.nan
        df["lvn_volume"] = np.nan
        return df

    profile_low = selected["low"].min() if min_price is None else min_price
    profile_high = selected["high"].max() if max_price is None else max_price

    if profile_high <= profile_low:
        df["lvn_price"] = np.nan
        df["lvn_volume"] = np.nan
        return df

    # Build price bins
    bins = np.arange(profile_low, profile_high + tick_size, tick_size)
    if len(bins) < 2:
        bins = np.array([profile_low, profile_low + tick_size])

    volume_profile = pd.Series(0.0, index=bins[:-1])

    # Distribute each bar's volume across all touched price bins
    for _, row in selected.iterrows():
        bar_low = row["low"]
        bar_high = row["high"]
        bar_vol = row["volume"]

        touched = volume_profile.index[
            (volume_profile.index + tick_size > bar_low) &
            (volume_profile.index <= bar_high)
        ]

        if len(touched) == 0:
            # fallback: assign to nearest bin by midpoint
            midpoint = (bar_low + bar_high) / 2
            nearest_idx = np.abs(volume_profile.index - midpoint).argmin()
            volume_profile.iloc[nearest_idx] += bar_vol
        else:
            volume_profile.loc[touched] += bar_vol / len(touched)

    non_zero = volume_profile[volume_profile > 0]

    if non_zero.empty:
        lvn_price = np.nan
        lvn_volume = np.nan
    else:
        lvn_price = non_zero.idxmin()
        lvn_volume = non_zero.min()

    df["lvn_price"] = lvn_price
    df["lvn_volume"] = lvn_volume

    return df

def add_fib_levels(
    df: pd.DataFrame,
    range_mask: pd.Series,
    high_col: str = "high",
    low_col: str = "low",
) -> pd.DataFrame:
    df = df.copy()

    required_cols = {high_col, low_col}
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    if len(range_mask) != len(df):
        raise ValueError("range_mask must be the same length as df")

    range_mask = range_mask.fillna(False).astype(bool)

    selected = df.loc[range_mask, [high_col, low_col]].copy()

    if selected.empty:
        df["fib_0_5"] = np.nan
        df["fib_0_618"] = np.nan
        df["fib_0_705"] = np.nan
        df["fib_0_79"] = np.nan
        df["range_high"] = np.nan
        df["range_low"] = np.nan
        return df

    range_high = selected[high_col].max()
    range_low = selected[low_col].min()
    range_size = range_high - range_low

    if pd.isna(range_size) or range_size <= 0:
        df["fib_0_5"] = np.nan
        df["fib_0_618"] = np.nan
        df["fib_0_705"] = np.nan
        df["fib_0_79"] = np.nan
        df["range_high"] = range_high
        df["range_low"] = range_low
        return df

    df["range_high"] = range_high
    df["range_low"] = range_low

    df["fib_0_5"] = range_low + (range_size * 0.5)
    df["fib_0_618"] = range_low + (range_size * 0.618)
    df["fib_0_705"] = range_low + (range_size * 0.705)
    df["fib_0_79"] = range_low + (range_size * 0.79)

    return df
