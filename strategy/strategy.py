import pandas as pd
from strategy.concepts import add_ema, add_fvg, add_vwap


def prepare_data(df: pd.DataFrame) -> pd.DataFrame:
    df = add_ema(df, 10)
    df = add_fvg(df)
    df = add_vwap(df)
    return df