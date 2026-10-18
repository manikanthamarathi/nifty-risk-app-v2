"""Signal scoring + budget-aware option trade planner (entry, stop-loss, target, lots)."""
from __future__ import annotations

import math
from datetime import date, datetime

import pandas as pd

from .indicators import atr, ema, macd, rsi
from .pricing import bs_delta, bs_price, round_tick, years_to_expiry

MIN_DELTA = 0.30

STYLES = {
    "Quick scalp (tight stop)": {"sl_atr": 1.0, "rr": 2.0, "note": "Short holding time. Needs fast decisions."},
    "Intraday balanced": {"sl_atr": 1.5, "rr": 2.0, "note": "Good default for beginners."},
    "Wide & patient": {"sl_atr": 2.5, "rr": 2.0, "note": "Fewer stop-outs, but bigger rupee loss per lot."},
}


def analyse(df: pd.DataFrame) -> dict:
    """Score the trend. Positive = bullish (CALL), negative = bearish (PUT)."""
    c = df["Close"]
    e9, e21, e50 = ema(c, 9), ema(c, 21), ema(c, 50)
    r = float(rsi(c).iloc[-1])
    _, _, hist = macd(c)
    a = float(atr(df).iloc[-1])
    spot = float(c.iloc[-1])

    score, reasons = 0, []

    if e9.iloc[-1] > e21.iloc[-1]:
        score += 2
        reasons.append(("bull", "Short-term average (EMA 9) is above the medium one (EMA 21) - buyers are in control."))
    else:
        score -= 2
        reasons.append(("bear", "Short-term average (EMA 9) is below EMA 21 - sellers are in control."))

    if spot > e50.iloc[-1]:
        score += 1
        reasons.append(("bull", "Price is above its longer trend line (EMA 50)."))
    else:
        score -= 1
        reasons.append(("bear", "Price is below its longer trend line (EMA 50)."))

    if r >= 75:
        score -= 1
        reasons.append(("warn", f"RSI is {r:.0f} - market looks stretched upward; a pullback is possible."))
    elif r >= 55:
        score += 1
        reasons.append(("bull", f"RSI is {r:.0f} - healthy upward momentum."))
    elif r <= 25:
        score += 1
        reasons.append(("warn", f"RSI is {r:.0f} - market looks stretched downward; a bounce is possible."))
    elif r <= 45:
        score -= 1
        reasons.append(("bear", f"RSI is {r:.0f} - weak, downward momentum."))
    else:
        reasons.append(("warn", f"RSI is {r:.0f} - neutral, no strong momentum."))

    h, h_prev = float(hist.iloc[-1]), float(hist.iloc[-2])
    if h > 0 and h > h_prev:
        score += 1
        reasons.append(("bull", "MACD is positive and strengthening."))
    elif h < 0 and h < h_prev:
        score -= 1
        reasons.append(("bear", "MACD is negative and getting weaker."))
    else:
        reasons.append(("warn", "MACD is fading - momentum is not confirming the trend."))

    if spot > float(c.iloc[-4]):
        score += 1
        reasons.append(("bull", "Last 3 candles closed higher overall."))
    else:
        score -= 1
        reasons.append(("bear", "Last 3 candles closed lower overall."))

    direction = "CALL" if score >= 3 else "PUT" if score <= -3 else "WAIT"
    strength = min(100, int(abs(score) / 6 * 100))
    return {
        "score": score, "direction": direction, "strength": strength, "reasons": reasons,
        "spot": spot, "atr": a, "rsi": r,
        "swing_high": float(df["High"].iloc[-6:].max()), "swing_low": float(df["Low"].iloc[-6:].min()),
        "ema21": float(e21.iloc[-1]), "ema50": float(e50.iloc[-1]),
    }


def build_plan(*, index: str, cfg: dict, spot: float, atr_pts: float, direction: str, budget: float,
               risk_pct: float, vix: float, expiry: date, now: datetime, style: str) -> dict:
    """Pick the best strike you can afford and compute entry / stop-loss / target using option repricing."""
    kind = direction  # 'CALL' | 'PUT'
    sigma = vix / 100.0
    T = years_to_expiry(expiry, now)
    lot, step = int(cfg["lot"]), int(cfg["step"])
    st = STYLES[style]
    sl_move = max(atr_pts * st["sl_atr"], spot * 0.0008)
    tgt_move = sl_move * st["rr"]
    sign = 1 if kind == "CALL" else -1
    s_sl, s_tgt = spot - sign * sl_move, spot + sign * tgt_move
    max_risk = budget * risk_pct / 100.0
    atm = round(spot / step) * step

    rows = []
    for k in range(-2, 5):  # from 2 strikes in-the-money to 4 out-of-the-money
        strike = atm + (k * step if kind == "CALL" else -k * step)
        prem = bs_price(spot, strike, T, sigma, kind)
        if prem < 1.0:
            continue
        p_sl = bs_price(s_sl, strike, T, sigma, kind)
        p_tg = bs_price(s_tgt, strike, T, sigma, kind)
        entry, sl, tg = round_tick(prem), round_tick(p_sl), round_tick(p_tg)
        loss_lot, gain_lot = (entry - sl) * lot, (tg - entry) * lot
        if loss_lot <= 0 or gain_lot <= 0:
            continue
        cost_lot = entry * lot
        lots_budget = int(budget // cost_lot)
        lots_risk = int(max_risk // loss_lot)
        lots = min(lots_budget, lots_risk)
        rows.append({
            "strike": int(strike), "delta": abs(bs_delta(spot, strike, T, sigma, kind)), "entry": entry, "sl": sl, "target": tg,
            "cost_lot": cost_lot, "loss_lot": loss_lot, "gain_lot": gain_lot, "lots_budget": lots_budget,
            "lots_risk": lots_risk, "lots": lots,
        })

    if not rows:
        return {"error": "Could not price any strikes. Check expiry date and volatility."}

    # Far out-of-the-money strikes (delta < 0.30) are lottery tickets that almost always expire worthless - never suggest them.
    rows = [r for r in rows if r["delta"] >= MIN_DELTA]
    if not rows:
        return {"error": "No suitable strikes found for this expiry. Try a later expiry date."}
    full = [r for r in rows if r["lots"] >= 1]
    pool = full or [r for r in rows if r["lots_budget"] >= 1]
    if not pool:
        cheapest = min(rows, key=lambda r: r["cost_lot"])
        return {"error": f"Your budget is too small for 1 lot of a sensible strike. The cheapest one here needs about ₹{cheapest['cost_lot']:,.0f}. "
                         "Raise your budget or pick an index with a smaller lot."}

    best = min(pool, key=lambda r: abs(r["delta"] - 0.5))  # closest to at-the-money = best balance of cost and movement
    over_risk = best["lots"] < 1
    if over_risk:
        best = dict(best, lots=1)

    lots = best["lots"]
    qty = lots * lot
    suffix = "CE" if kind == "CALL" else "PE"
    return {
        "kind": kind, "symbol": f"{index} {best['strike']} {suffix}", "index": index, "strike": best["strike"],
        "expiry": expiry, "lot": lot, "lots": lots, "qty": qty,
        "entry": best["entry"], "sl": best["sl"], "target": best["target"], "delta": best["delta"],
        "capital_used": best["entry"] * qty, "max_loss": best["loss_lot"] * lots, "max_profit": best["gain_lot"] * lots,
        "rr": best["gain_lot"] / best["loss_lot"], "over_risk": over_risk, "max_risk_allowed": max_risk,
        "spot": spot, "spot_sl": s_sl, "spot_target": s_tgt, "alternatives": pd.DataFrame(rows),
        "style_note": st["note"],
    }
