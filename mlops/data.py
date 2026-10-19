"""Data loading + fingerprinting, so every MLflow run records exactly which data it was trained on."""
import hashlib
import numpy as np
import pandas as pd

INDICES = {"Nifty Metal": "nifty-metal-trend", "Nifty 50": "nifty-50-trend"}


def load_daily(name: str) -> pd.Series:
    if name == "Nifty Metal":
        return pd.read_csv("nifty_metal_official.csv", parse_dates=["date"]).set_index("date")["close"]
    import yfinance as yf
    return yf.download("^NSEI", start="2007-09-01", auto_adjust=True, progress=False)["Close"].squeeze().dropna()


def monthly_log(daily: pd.Series) -> pd.Series:
    return np.log(daily.resample("M").last())


def fingerprint(daily: pd.Series) -> str:
    return hashlib.sha256(pd.util.hash_pandas_object(daily, index=True).values.tobytes()).hexdigest()[:16]
