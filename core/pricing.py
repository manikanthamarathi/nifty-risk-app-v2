"""Black-Scholes option pricing (free alternative to a paid option-chain feed) and expiry helpers."""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta

RISK_FREE = 0.07


def _ncdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _d1(S, K, T, sigma, r=RISK_FREE):
    return (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))


def bs_price(S: float, K: float, T: float, sigma: float, kind: str, r: float = RISK_FREE) -> float:
    """kind: 'CALL' or 'PUT'. T in years, sigma as a fraction (0.14 = 14%)."""
    if T <= 0 or sigma <= 0:
        return max(S - K, 0.0) if kind == "CALL" else max(K - S, 0.0)
    d1 = _d1(S, K, T, sigma, r)
    d2 = d1 - sigma * math.sqrt(T)
    if kind == "CALL":
        return S * _ncdf(d1) - K * math.exp(-r * T) * _ncdf(d2)
    return K * math.exp(-r * T) * _ncdf(-d2) - S * _ncdf(-d1)


def bs_delta(S: float, K: float, T: float, sigma: float, kind: str, r: float = RISK_FREE) -> float:
    if T <= 0 or sigma <= 0:
        return 1.0 if (kind == "CALL" and S > K) or (kind == "PUT" and S < K) else 0.0
    d1 = _d1(S, K, T, sigma, r)
    return _ncdf(d1) if kind == "CALL" else _ncdf(d1) - 1


def round_tick(x: float) -> float:
    """Options trade in 0.05 ticks."""
    return max(0.05, round(round(x / 0.05) * 0.05, 2))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    nxt = date(year + (month == 12), month % 12 + 1, 1)
    d = nxt - timedelta(days=1)
    while d.weekday() != weekday:
        d -= timedelta(days=1)
    return d


def next_expiry(kind: str, weekday: int, now: datetime) -> date:
    """kind: 'weekly' (next given weekday) or 'monthly' (last given weekday of month). Verify on NSE/BSE."""
    after_close = (now.hour, now.minute) >= (15, 30)
    today = now.date()
    if kind == "weekly":
        ahead = (weekday - today.weekday()) % 7
        if ahead == 0 and after_close:
            ahead = 7
        return today + timedelta(days=ahead)
    cand = _last_weekday_of_month(today.year, today.month, weekday)
    if cand < today or (cand == today and after_close):
        y, m = (today.year + (today.month == 12), today.month % 12 + 1)
        cand = _last_weekday_of_month(y, m, weekday)
    return cand


def years_to_expiry(expiry: date, now: datetime) -> float:
    end = datetime(expiry.year, expiry.month, expiry.day, 15, 30)
    secs = max((end - now).total_seconds(), 30 * 60)  # never below 30 min, avoids divide-by-zero
    return secs / (365 * 24 * 3600)
