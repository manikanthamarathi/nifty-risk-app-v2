"""SQLite storage: paper trades + imported contract-note ledger."""
from __future__ import annotations

import sqlite3
from datetime import datetime

import pandas as pd
import streamlit as st

DB_PATH = "indicerisk.db"

LEDGER_COLS = ["trade_date", "order_no", "trade_time", "contract", "side", "qty", "gross_rate",
               "brokerage_unit", "net_rate", "net_total"]


@st.cache_resource
def conn() -> sqlite3.Connection:
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("""CREATE TABLE IF NOT EXISTS paper_trades (
        id INTEGER PRIMARY KEY AUTOINCREMENT, opened_at TEXT, symbol TEXT, kind TEXT, qty INTEGER,
        entry REAL, sl REAL, target REAL, status TEXT, exit_price REAL, closed_at TEXT, pnl REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS trade_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT, order_no TEXT, trade_time TEXT, contract TEXT,
        side TEXT, qty INTEGER, gross_rate REAL, brokerage_unit REAL, net_rate REAL, net_total REAL)""")
    c.commit()
    return c


def add_paper_trade(symbol: str, kind: str, qty: int, entry: float, sl: float, target: float) -> int:
    cur = conn().execute(
        "INSERT INTO paper_trades (opened_at, symbol, kind, qty, entry, sl, target, status) VALUES (?,?,?,?,?,?,?,'OPEN')",
        (datetime.now().strftime("%Y-%m-%d %H:%M"), symbol, kind, int(qty), float(entry), float(sl), float(target)))
    conn().commit()
    return cur.lastrowid


def paper_trades() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM paper_trades ORDER BY id DESC", conn())


def close_paper_trade(trade_id: int, exit_price: float) -> None:
    row = conn().execute("SELECT entry, qty FROM paper_trades WHERE id=? AND status='OPEN'", (trade_id,)).fetchone()
    if not row:
        return
    pnl = (float(exit_price) - row[0]) * row[1]  # we only ever BUY options, so profit = (exit - entry) x qty
    conn().execute("UPDATE paper_trades SET status='CLOSED', exit_price=?, closed_at=?, pnl=? WHERE id=?",
                   (float(exit_price), datetime.now().strftime("%Y-%m-%d %H:%M"), pnl, trade_id))
    conn().commit()


def delete_paper_trade(trade_id: int) -> None:
    conn().execute("DELETE FROM paper_trades WHERE id=?", (trade_id,))
    conn().commit()


def replace_ledger(df: pd.DataFrame) -> None:
    conn().execute("DELETE FROM trade_logs")
    df[LEDGER_COLS].to_sql("trade_logs", conn(), if_exists="append", index=False)
    conn().commit()


def append_ledger(df: pd.DataFrame) -> None:
    df[LEDGER_COLS].to_sql("trade_logs", conn(), if_exists="append", index=False)
    conn().commit()


def ledger() -> pd.DataFrame:
    return pd.read_sql_query("SELECT * FROM trade_logs ORDER BY id", conn())
