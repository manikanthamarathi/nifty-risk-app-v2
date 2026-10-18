"""Contract-note import (CSV, or PDF with tables) -> canonical ledger rows."""
from __future__ import annotations

import pandas as pd

ALIASES = {
    "trade_date": ["trade_date", "date", "trade date"],
    "order_no": ["order_no", "order no", "order number", "order_number", "orderno"],
    "trade_time": ["trade_time", "time", "trade time"],
    "contract": ["contract", "symbol", "scrip", "instrument", "tradingsymbol"],
    "side": ["side", "buy/sell", "b/s", "action", "buy_sell", "trade type"],
    "qty": ["qty", "quantity", "traded qty"],
    "gross_rate": ["gross_rate", "gross rate", "price", "rate", "trade price"],
    "brokerage_unit": ["brokerage_unit", "brokerage per unit", "brokerage", "brokerage/unit"],
    "net_rate": ["net_rate", "net rate"],
    "net_total": ["net_total", "net total", "net amount", "net total (before levies)", "amount"],
}
SAMPLE = pd.DataFrame([
    {"trade_date": "2026-10-16", "order_no": "SAMPLE-001", "trade_time": "10:12:04", "contract": "NIFTY 23100 CE",
     "side": "B", "qty": 65, "gross_rate": 85.50, "brokerage_unit": 0.0769, "net_rate": 85.5769, "net_total": -5562.50},
    {"trade_date": "2026-10-16", "order_no": "SAMPLE-002", "trade_time": "11:40:31", "contract": "NIFTY 23100 CE",
     "side": "S", "qty": 65, "gross_rate": 112.00, "brokerage_unit": 0.0769, "net_rate": 111.9231, "net_total": 7275.00},
])


def normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    out = pd.DataFrame()
    for canon, names in ALIASES.items():
        hit = next((n for n in names if n in df.columns), None)
        out[canon] = df[hit] if hit else None
    missing = [c for c in ("contract", "side", "qty", "gross_rate") if out[c].isna().all()]
    if missing:
        raise ValueError("Could not find these columns in your file: " + ", ".join(missing) +
                         ". Expected headers like Contract, Side (B/S), Qty, Price.")
    out["side"] = out["side"].astype(str).str.strip().str.upper().str[0].map({"B": "B", "S": "S"})
    out = out.dropna(subset=["side"])
    for c in ("qty", "gross_rate", "brokerage_unit", "net_rate", "net_total"):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["qty"] = out["qty"].fillna(0).astype(int)
    out["brokerage_unit"] = out["brokerage_unit"].fillna(0.0)
    out["net_rate"] = out["net_rate"].fillna(
        out["gross_rate"] + out["brokerage_unit"] * out["side"].map({"B": 1, "S": -1}))
    out["net_total"] = out["net_total"].fillna(out["net_rate"] * out["qty"] * out["side"].map({"B": -1, "S": 1}))
    for c in ("trade_date", "order_no", "trade_time"):
        out[c] = out[c].fillna("").astype(str)
    out["contract"] = out["contract"].astype(str)
    return out.reset_index(drop=True)


def parse_csv(file) -> pd.DataFrame:
    return normalise(pd.read_csv(file))


def parse_pdf(file) -> pd.DataFrame:
    import pdfplumber

    frames = []
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if len(table) > 1:
                    frames.append(pd.DataFrame(table[1:], columns=[str(h) for h in table[0]]))
    if not frames:
        raise ValueError("No tables found in this PDF (scanned PDFs are not supported). Try the CSV export from your broker.")
    return normalise(pd.concat(frames, ignore_index=True))


def summarise(df: pd.DataFrame) -> pd.DataFrame:
    """Per-contract realised P&L. A contract is 'Open' if bought and sold quantities differ."""
    g = df.assign(bq=df["qty"].where(df["side"] == "B", 0), sq=df["qty"].where(df["side"] == "S", 0)) \
          .groupby("contract").agg(bought=("bq", "sum"), sold=("sq", "sum"), net_pnl=("net_total", "sum")).reset_index()
    g["status"] = g.apply(lambda r: "Closed" if r.bought == r.sold else "Open / partial", axis=1)
    return g
