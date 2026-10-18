"""Free market data (Yahoo Finance via yfinance) with a clearly-labelled demo fallback."""
from __future__ import annotations

import os
from datetime import datetime, time, timedelta

import numpy as np
import pandas as pd
import streamlit as st

# lot_size / strike_step are editable in the app (exchanges revise lot sizes - always verify).
INDICES = {
    "NIFTY": {"ticker": "^NSEI", "lot": 65, "step": 50, "demo_base": 23000.0, "expiry": ("weekly", 1)},
    "BANKNIFTY": {"ticker": "^NSEBANK", "lot": 30, "step": 100, "demo_base": 50000.0, "expiry": ("monthly", 1)},
    "FINNIFTY": {"ticker": "NIFTY_FIN_SERVICE.NS", "lot": 60, "step": 50, "demo_base": 23500.0, "expiry": ("monthly", 1)},
    "SENSEX": {"ticker": "^BSESN", "lot": 20, "step": 100, "demo_base": 75000.0, "expiry": ("weekly", 3)},
}

OFFLINE = os.environ.get("INDICERISK_OFFLINE") == "1"


def ist_now() -> datetime:
    """Current time in IST as a naive datetime (works whatever the server timezone is)."""
    return datetime.utcnow() + timedelta(hours=5, minutes=30)


def market_status(now: datetime | None = None) -> tuple[bool, str]:
    now = now or ist_now()
    if now.weekday() >= 5:
        return False, "Market closed (weekend)"
    if time(9, 15) <= now.time() <= time(15, 30):
        return True, "Market open"
    return False, "Market closed (opens 9:15 AM IST)"


def _demo_candles(base: float, seed_key: str) -> pd.DataFrame:
    rng = np.random.default_rng(abs(hash(seed_key)) % (2**32))
    days = pd.bdate_range(end=ist_now().date(), periods=6)
    rows, price = [], base
    for d in days:
        start = pd.Timestamp(d) + pd.Timedelta(hours=9, minutes=15)
        for i in range(25):
            o = price
            drift = rng.normal(0, base * 0.0011)
            c = o + drift
            h = max(o, c) + abs(rng.normal(0, base * 0.0005))
            l = min(o, c) - abs(rng.normal(0, base * 0.0005))
            rows.append((start + pd.Timedelta(minutes=15 * i), o, h, l, c))
            price = c
    df = pd.DataFrame(rows, columns=["Time", "Open", "High", "Low", "Close"]).set_index("Time")
    return df


@st.cache_data(ttl=120, show_spinner=False)
def fetch_candles(index_name: str, interval: str = "15m", period: str = "5d") -> tuple[pd.DataFrame, bool]:
    """Returns (candles, is_demo). Falls back to demo data if the free feed is unreachable."""
    cfg = INDICES[index_name]
    if not OFFLINE:
        try:
            import yfinance as yf

            df = yf.download(cfg["ticker"], interval=interval, period=period, progress=False, auto_adjust=False, timeout=10)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df = df.dropna(subset=["Close"])
            if len(df) >= 60:
                idx = df.index
                if getattr(idx, "tz", None) is not None:
                    idx = idx.tz_convert("Asia/Kolkata").tz_localize(None)
                df = df[["Open", "High", "Low", "Close"]].copy()
                df.index = idx
                df.index.name = "Time"
                return df, False
        except Exception:
            pass
    return _demo_candles(cfg["demo_base"], index_name), True


@st.cache_data(ttl=300, show_spinner=False)
def fetch_vix() -> tuple[float, bool]:
    """India VIX (annualised implied volatility, in %). Falls back to 14."""
    if not OFFLINE:
        try:
            import yfinance as yf

            df = yf.download("^INDIAVIX", period="5d", interval="1d", progress=False, timeout=10)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            v = float(df["Close"].dropna().iloc[-1])
            if 5 <= v <= 80:
                return v, False
        except Exception:
            pass
    return 14.0, True


def day_change(df: pd.DataFrame) -> tuple[float, float]:
    """(last price, % change vs previous session close)."""
    last = float(df["Close"].iloc[-1])
    dates = df.index.normalize()
    prev = df[dates < dates[-1]]
    if prev.empty:
        return last, 0.0
    p = float(prev["Close"].iloc[-1])
    return last, (last / p - 1) * 100
