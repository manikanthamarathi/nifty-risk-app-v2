"""All app pages. Each page is a function; app.py routes between them."""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core import db
from core.broker import shoonya_buy_limit, shoonya_login, telegram_send
from core.data import INDICES, day_change, fetch_candles, fetch_vix, ist_now, market_status
from core.indicators import ema
from core.parser import SAMPLE, parse_csv, parse_pdf, summarise
from core.pricing import next_expiry
from core.strategy import STYLES, analyse, build_plan
from ui.styles import DISCLAIMER, card, hero, inr, meter, pill, pills, tile


def go_to(page: str) -> None:
    st.session_state["nav"] = page


# ---------------------------------------------------------------- HOME
def page_home() -> None:
    hero("⚡ IndiceRisk Pro", "Your free, beginner-friendly assistant for Indian index options. "
         "Pick an index, tell it your budget - it suggests the option, entry, stop-loss and target.")
    c1, c2, c3 = st.columns(3)
    c1.markdown(card("Pick an index & budget", "Choose NIFTY, BANKNIFTY, FINNIFTY or SENSEX and how much money you can use. Nothing else to set up.", "1"), unsafe_allow_html=True)
    c2.markdown(card("Get a ready trade plan", "The app reads the trend, picks a strike you can afford, and shows buy price, stop-loss, target and how many lots.", "2"), unsafe_allow_html=True)
    c3.markdown(card("Practise before real money", "Save the idea as a paper trade, track it, and learn from the results. No broker needed.", "3"), unsafe_allow_html=True)
    st.button("🎯 Get my first trade idea", type="primary", on_click=go_to, args=("🎯 Trade Ideas",))

    st.markdown("#### Market snapshot")
    ok, msg = market_status()
    cols = st.columns(4)
    demo_any = False
    for col, name in zip(cols, INDICES):
        df, demo = fetch_candles(name)
        demo_any |= demo
        last, chg = day_change(df)
        col.markdown(tile(name, f"{last:,.0f}", f"{chg:+.2f}% vs prev close", "good" if chg >= 0 else "bad"), unsafe_allow_html=True)
    vix, vix_demo = fetch_vix()
    pills(pill(msg, "green" if ok else "red"), pill(f"India VIX {vix:.1f}"),
          pill("DEMO data (feed unreachable)" if demo_any else "Free delayed data (Yahoo Finance)", "amber" if demo_any else "green"))
    st.markdown(DISCLAIMER, unsafe_allow_html=True)


# ---------------------------------------------------------------- TRADE IDEAS
def _chart(df: pd.DataFrame, plan: dict | None) -> go.Figure:
    d = df.iloc[-100:]
    fig = go.Figure(go.Candlestick(x=d.index, open=d["Open"], high=d["High"], low=d["Low"], close=d["Close"], name="Price",
                                   increasing_line_color="#22c55e", decreasing_line_color="#ef4444"))
    fig.add_trace(go.Scatter(x=d.index, y=ema(df["Close"], 21).iloc[-100:], name="EMA 21", line=dict(color="#a5b4fc", width=1.5)))
    fig.add_trace(go.Scatter(x=d.index, y=ema(df["Close"], 50).iloc[-100:], name="EMA 50", line=dict(color="#f59e0b", width=1.5)))
    if plan:
        for y, label, col in ((plan["spot"], "Entry", "#a5b4fc"), (plan["spot_sl"], "Stop-loss (index)", "#ef4444"),
                              (plan["spot_target"], "Target (index)", "#22c55e")):
            fig.add_hline(y=y, line_dash="dash", line_color=col, annotation_text=label, annotation_position="right")
    fig.update_layout(template="plotly_dark", height=420, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", y=1.08))
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"]), dict(bounds=[15.5, 9.25], pattern="hour")])
    return fig


def page_trade() -> None:
    hero("🎯 Trade Ideas", "Answer 3 simple questions. The app does the rest.")
    index = st.radio("1️⃣  Which index?", list(INDICES), horizontal=True, key="t_index")
    cfg = dict(INDICES[index])
    c1, c2, c3 = st.columns(3)
    budget = c1.number_input("2️⃣  Money you can use for this trade (₹)", 2000, 10_000_000, 25000, 1000, key="t_budget",
                             help="The most premium (money) you are willing to put into this one trade.")
    risk_pct = c2.slider("3️⃣  Max loss you accept (% of that money)", 1.0, 20.0, 8.0, 0.5, key="t_risk",
                         help="If the stop-loss is hit you lose about this much or less. Smaller = safer, but may allow fewer lots.")
    style = c3.selectbox("Trade style", list(STYLES), index=1, key="t_style", help="Controls how tight or wide your stop-loss is.")
    st.caption(f"ℹ️ {STYLES[style]['note']}")

    now = ist_now()
    exp_kind, exp_wd = cfg["expiry"]
    with st.expander("⚙️ Advanced (optional - safe to ignore)"):
        a1, a2, a3, a4 = st.columns(4)
        cfg["lot"] = a1.number_input("Lot size", 1, 2000, cfg["lot"], key=f"lot_{index}", help="Check the current lot size on the exchange website.")
        cfg["step"] = a2.number_input("Strike gap", 5, 500, cfg["step"], key=f"step_{index}")
        expiry = a3.date_input("Expiry date", next_expiry(exp_kind, exp_wd, now), key=f"exp_{index}", help="Default is a guess - confirm on NSE/BSE.")
        override = a4.selectbox("Practice mode", ["Follow the signal", "Force CALL", "Force PUT"], key="t_force",
                                help="Ignore the signal and see a plan for a direction of your choice (for learning only).")

    with st.spinner("Reading the market..."):
        df, demo = fetch_candles(index)
        vix, vix_demo = fetch_vix()
        res = analyse(df)

    ok, msg = market_status(now)
    pills(pill(msg, "green" if ok else "red"), pill(f"{index} {res['spot']:,.2f}"), pill(f"India VIX {vix:.1f}" + (" (default)" if vix_demo else "")),
          pill("DEMO data - not real prices" if demo else "Free delayed data", "amber" if demo else "green"))
    if demo:
        st.warning("The free data feed could not be reached, so **demo data** is shown. Do not trade on it.")
    if not ok:
        st.info("The market is closed, so this uses the last available prices. Re-check after 9:15 AM IST on the next trading day.")

    direction = {"Force CALL": "CALL", "Force PUT": "PUT"}.get(override, res["direction"])
    cls, colour = {"CALL": ("call", "green"), "PUT": ("put", "red"), "WAIT": ("wait", "amber")}[direction]
    headline = {"CALL": "📈 Market looks UP - consider a CALL (CE)", "PUT": "📉 Market looks DOWN - consider a PUT (PE)",
                "WAIT": "⏸️ No clear trend - best move is to WAIT"}[direction]
    st.markdown(f'<div class="signal {cls}"><div class="big">{headline}</div>'
                f'<div class="sub">Signal strength: {res["strength"]}% (this is how many indicators agree - not a chance of winning)'
                f'{" · practice mode on" if override != "Follow the signal" else ""}</div>{meter(res["strength"] or 8, colour)}</div>', unsafe_allow_html=True)

    plan = None
    if direction == "WAIT":
        st.markdown(card("Why waiting is a good trade", "When indicators disagree, option buyers usually lose money to time decay. "
                                                         "Skipping a bad setup protects your capital. Check back in 15-30 minutes, "
                                                         "or use <b>Practice mode</b> under Advanced to explore a plan anyway."), unsafe_allow_html=True)
    else:
        plan = build_plan(index=index, cfg=cfg, spot=res["spot"], atr_pts=res["atr"], direction=direction, budget=float(budget),
                          risk_pct=risk_pct, vix=vix, expiry=expiry, now=now, style=style)
        if "error" in plan:
            st.error(plan["error"])
            plan = None
        else:
            _show_plan(plan, budget, df)

    st.markdown("##### Why the app says this")
    for kind, text in res["reasons"]:
        st.markdown(f'<div class="reason {kind}">{"✅" if kind == "bull" else "🔻" if kind == "bear" else "⚠️"} {text}</div>', unsafe_allow_html=True)

    st.plotly_chart(_chart(df, plan), width="stretch")
    if plan:
        with st.expander("🔍 Other strikes I considered"):
            alt = plan["alternatives"].copy()
            alt = alt.rename(columns={"strike": "Strike", "delta": "Delta", "entry": "Buy at", "sl": "Stop-loss", "target": "Target",
                                      "cost_lot": "Cost / lot", "loss_lot": "Loss / lot", "gain_lot": "Profit / lot", "lots": "Lots allowed"})
            st.dataframe(alt[["Strike", "Delta", "Buy at", "Stop-loss", "Target", "Cost / lot", "Loss / lot", "Profit / lot", "Lots allowed"]]
                         .style.format({"Delta": "{:.2f}", "Cost / lot": "₹{:,.0f}", "Loss / lot": "₹{:,.0f}", "Profit / lot": "₹{:,.0f}"}),
                         width="stretch", hide_index=True)
            st.caption("Delta ≈ how much the option price moves for a 1-point index move. ~0.5 is the sweet spot between cost and movement.")
    st.markdown(DISCLAIMER, unsafe_allow_html=True)


def _show_plan(plan: dict, budget: float, df: pd.DataFrame) -> None:
    typ = "CALL (CE)" if plan["kind"] == "CALL" else "PUT (PE)"
    st.markdown(f'<div class="trade"><div class="tag">Your trade idea</div><div class="head">BUY {plan["symbol"]} &nbsp;·&nbsp; {plan["lots"]} lot'
                f'{"s" if plan["lots"] > 1 else ""} ({plan["qty"]} qty)</div>'
                f'<p style="margin:6px 0 0 0;color:#b6bfdc">{typ} · expiry {plan["expiry"]:%d %b %Y} · '
                f'enter when the {plan["index"]} is near <b>{plan["spot"]:,.0f}</b> and the option trades near <b>{inr(plan["entry"], 2)}</b></p></div>',
                unsafe_allow_html=True)
    if plan["over_risk"]:
        st.warning(f"1 lot risks about {inr(plan['max_loss'])}, above your limit of {inr(plan['max_risk_allowed'])}. "
                   "Raise the risk %, choose a tighter style, or skip this trade.")
    c = st.columns(4)
    c[0].markdown(tile("Buy at (entry)", inr(plan["entry"], 2), "per unit, estimated", "info"), unsafe_allow_html=True)
    c[1].markdown(tile("Stop-loss", inr(plan["sl"], 2), f"exit if premium falls here · index ≈ {plan['spot_sl']:,.0f}", "bad"), unsafe_allow_html=True)
    c[2].markdown(tile("Target", inr(plan["target"], 2), f"book profit here · index ≈ {plan['spot_target']:,.0f}", "good"), unsafe_allow_html=True)
    c[3].markdown(tile("Risk : Reward", f"1 : {plan['rr']:.1f}", "for every ₹1 risked", "info"), unsafe_allow_html=True)
    st.write("")
    c = st.columns(3)
    c[0].markdown(tile("Money needed", inr(plan["capital_used"]), f"of your {inr(budget)} budget", "info"), unsafe_allow_html=True)
    c[1].markdown(tile("Max loss (if stop hits)", inr(plan["max_loss"]), f"limit was {inr(plan['max_risk_allowed'])}", "bad"), unsafe_allow_html=True)
    c[2].markdown(tile("Profit (if target hits)", inr(plan["max_profit"]), "before brokerage & taxes", "good"), unsafe_allow_html=True)
    st.write("")
    with st.expander("✅ Beginner checklist before you enter", expanded=True):
        st.markdown(
            f"1. Open your broker app and check the **live premium** of {plan['symbol']}. If it is far from {inr(plan['entry'], 2)}, redo the plan with that price in the Risk Calculator.\n"
            f"2. Place a **limit buy** at about {inr(plan['entry'], 2)} - avoid market orders on options.\n"
            f"3. **Immediately** set a stop-loss order at {inr(plan['sl'], 2)}.\n"
            f"4. When profit reaches about half the target, move your stop-loss up to your entry price (risk-free trade).\n"
            f"5. Exit everything before **3:15 PM** - do not hold buying positions into expiry day close.\n"
            f"6. Stop trading for the day if you lose more than 2 trades in a row.")
    b1, b2 = st.columns(2)
    if b1.button("📝 Save as paper trade (practice)", type="primary"):
        tid = db.add_paper_trade(plan["symbol"], plan["kind"], plan["qty"], plan["entry"], plan["sl"], plan["target"])
        st.success(f"Saved as paper trade #{tid}. Track it on the Paper Trading page.")
    if b2.button("📲 Send this plan to Telegram"):
        tok, chat = st.session_state.get("tg_token"), st.session_state.get("tg_chat")
        if not (tok and chat):
            st.info("Set up Telegram first on the 'Broker & Alerts' page (takes 2 minutes).")
        else:
            ok, msg = telegram_send(tok, chat, f"IndiceRisk idea: BUY {plan['symbol']} x{plan['qty']}\nEntry ~{plan['entry']}  SL {plan['sl']}  Target {plan['target']}\n(model estimates - verify live)")
            (st.success if ok else st.error)(msg)
    st.session_state["last_plan"] = plan


# ---------------------------------------------------------------- RISK CALCULATOR
def page_risk() -> None:
    hero("🛡️ Risk Calculator", "Already have your own entry, stop-loss and target? See exactly how many lots are safe.")
    c1, c2 = st.columns(2)
    capital = c1.number_input("Trading capital (₹)", 5000.0, 1e8, 50000.0, 5000.0)
    risk_pct = c1.slider("Risk per trade (% of capital)", 0.5, 5.0, 2.0, 0.5, help="Most professionals risk 1-2%.")
    lot = c1.number_input("Lot size", 1, 2000, 65)
    entry = c2.number_input("Entry premium (₹)", 0.05, 100000.0, 85.0, 0.05)
    sl = c2.number_input("Stop-loss premium (₹)", 0.05, 100000.0, 75.0, 0.05)
    tgt = c2.number_input("Target premium (₹)", 0.05, 100000.0, 115.0, 0.05)
    if sl >= entry:
        st.error("For buying options, stop-loss must be BELOW your entry.")
        return
    if tgt <= entry:
        st.error("Target must be ABOVE your entry.")
        return
    max_risk = capital * risk_pct / 100
    loss_lot, gain_lot, cost_lot = (entry - sl) * lot, (tgt - entry) * lot, entry * lot
    lots_risk, lots_cap = int(max_risk // loss_lot), int(capital // cost_lot)
    lots = min(lots_risk, lots_cap)
    if lots < 1:
        st.warning(f"Even 1 lot breaks your rules: it risks {inr(loss_lot)} (limit {inr(max_risk)}) and costs {inr(cost_lot)}. Tighten the stop-loss or raise the risk %.")
        lots = 0
    c = st.columns(4)
    c[0].markdown(tile("Lots to buy", str(lots), f"{lots * lot} qty", "info"), unsafe_allow_html=True)
    c[1].markdown(tile("Money needed", inr(cost_lot * lots), f"{cost_lot * lots / capital * 100:.0f}% of capital", "info"), unsafe_allow_html=True)
    c[2].markdown(tile("Max loss", inr(loss_lot * lots), f"allowed {inr(max_risk)}", "bad"), unsafe_allow_html=True)
    c[3].markdown(tile("Profit at target", inr(gain_lot * lots), f"1 : {(tgt - entry) / (entry - sl):.2f} reward", "good"), unsafe_allow_html=True)
    st.write("")
    be = (entry - sl) / ((tgt - entry) + (entry - sl)) * 100
    st.info(f"With this reward-to-risk you only need to win about **{be:.0f}%** of your trades to break even (before brokerage).")
    st.markdown("##### Growing your account (compounding)")
    wins = st.slider("Imagine this many winning trades in a row", 1, 20, 5)
    st.line_chart(pd.Series([capital * (1 + risk_pct / 100 * ((tgt - entry) / (entry - sl))) ** i for i in range(wins + 1)], name="Capital (₹)"))
    st.caption("Illustration only - real results include losses, brokerage and taxes.")


# ---------------------------------------------------------------- PAPER TRADING
def page_paper() -> None:
    hero("📝 Paper Trading", "Practice with zero risk. Close trades at the price you would have got and watch your results build.")
    df = db.paper_trades()
    closed = df[df["status"] == "CLOSED"] if not df.empty else df
    wins = int((closed["pnl"] > 0).sum()) if not closed.empty else 0
    total = float(closed["pnl"].sum()) if not closed.empty else 0.0
    c = st.columns(4)
    c[0].markdown(tile("Total P&L", inr(total), "closed trades", "good" if total >= 0 else "bad"), unsafe_allow_html=True)
    c[1].markdown(tile("Win rate", f"{wins / len(closed) * 100:.0f}%" if len(closed) else "-", f"{wins} of {len(closed)} trades", "info"), unsafe_allow_html=True)
    c[2].markdown(tile("Open trades", str(int((df["status"] == "OPEN").sum()) if not df.empty else 0), "waiting to close", "info"), unsafe_allow_html=True)
    c[3].markdown(tile("Best trade", inr(float(closed["pnl"].max())) if len(closed) else "-", "", "good"), unsafe_allow_html=True)
    st.write("")
    if df.empty:
        st.info("No paper trades yet. Go to **Trade Ideas** and press *Save as paper trade*.")
        return
    openp = df[df["status"] == "OPEN"]
    if not openp.empty:
        st.markdown("##### Close a trade")
        x1, x2, x3 = st.columns([2, 1, 1])
        pick = x1.selectbox("Open trade", openp["id"], format_func=lambda i: f"#{i} - {openp[openp.id == i].iloc[0].symbol} (entry {openp[openp.id == i].iloc[0].entry})")
        row = openp[openp.id == pick].iloc[0]
        exit_p = x2.number_input("Exit price (₹)", 0.05, 100000.0, float(row.target), 0.05)
        x3.write("")
        if x3.button("Close trade", type="primary"):
            db.close_paper_trade(int(pick), exit_p)
            st.rerun()
    if not closed.empty:
        st.markdown("##### Your equity curve")
        st.line_chart(closed.sort_values("id")["pnl"].cumsum().reset_index(drop=True), height=220)
    st.markdown("##### All trades")
    st.dataframe(df, width="stretch", hide_index=True)
    d1, d2 = st.columns([1, 3])
    del_id = d1.number_input("Delete trade #", 0, 10**9, 0)
    if d2.button("🗑️ Delete") and del_id:
        db.delete_paper_trade(int(del_id))
        st.rerun()


# ---------------------------------------------------------------- LEDGER
def page_ledger() -> None:
    hero("📊 P&L Ledger", "Import your broker's contract note (CSV or text-based PDF) and see your real profit & loss per contract.")
    up = st.file_uploader("Upload contract note", type=["csv", "pdf"])
    c1, c2 = st.columns(2)
    if up is not None and c1.button("Import file", type="primary"):
        try:
            parsed = parse_pdf(up) if up.name.lower().endswith(".pdf") else parse_csv(up)
            db.append_ledger(parsed)
            st.success(f"Imported {len(parsed)} trades.")
        except Exception as e:
            st.error(str(e))
    if c2.button("Load sample data"):
        db.replace_ledger(SAMPLE)
        st.success("Sample trades loaded (they replace what is shown).")
    led = db.ledger()
    if led.empty:
        st.info("Nothing here yet. Upload a file or load the sample.")
        return
    summ = summarise(led)
    total = float(summ.loc[summ.status == "Closed", "net_pnl"].sum())
    c = st.columns(3)
    c[0].markdown(tile("Realised P&L", inr(total, 2), "closed contracts only", "good" if total >= 0 else "bad"), unsafe_allow_html=True)
    c[1].markdown(tile("Trades imported", str(len(led)), "", "info"), unsafe_allow_html=True)
    c[2].markdown(tile("Contracts", str(len(summ)), "", "info"), unsafe_allow_html=True)
    st.markdown("##### Profit & loss by contract")
    st.dataframe(summ.style.format({"net_pnl": "₹{:,.2f}"}), width="stretch", hide_index=True)
    st.markdown("##### Every trade")
    st.dataframe(led, width="stretch", hide_index=True)
    st.download_button("📥 Download ledger CSV", led.to_csv(index=False).encode(), "pnl_ledger.csv", "text/csv")
    if st.button("Clear ledger"):
        db.replace_ledger(led.iloc[0:0])
        st.rerun()


# ---------------------------------------------------------------- BROKER & ALERTS
def page_connect() -> None:
    hero("🔗 Broker & Alerts", "Optional extras. The app works fully without any of this.")
    t1, t2 = st.tabs(["📲 Telegram alerts (free)", "🏦 Shoonya broker (advanced)"])
    with t1:
        st.markdown("1. In Telegram, chat with **@BotFather** → `/newbot` → copy the token.\n2. Send any message to your new bot, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` and copy the number after `\"chat\":{\"id\":`.")
        tok = st.text_input("Bot token", type="password", value=st.session_state.get("tg_token", ""))
        chat = st.text_input("Chat ID", value=st.session_state.get("tg_chat", ""))
        if st.button("Save & send test message"):
            st.session_state["tg_token"], st.session_state["tg_chat"] = tok, chat
            ok, msg = telegram_send(tok, chat, "✅ IndiceRisk test alert")
            (st.success if ok else st.error)(msg)
        st.caption("Kept only for this browser session - never written to disk.")
    with t2:
        st.warning("Real orders use real money. Credentials stay in memory for this session only. This integration needs a real Shoonya account and has not been tested end-to-end - try with 1 lot first.")
        a, b = st.columns(2)
        uid = a.text_input("User ID")
        pw = a.text_input("Password", type="password")
        f2 = a.text_input("TOTP / OTP", type="password")
        vc = b.text_input("Vendor code")
        sec = b.text_input("API secret", type="password")
        if st.button("Connect to Shoonya"):
            api, msg = shoonya_login(uid, pw, f2, vc, sec)
            st.session_state["shoonya"] = api
            (st.success if api else st.error)(msg)
        api = st.session_state.get("shoonya")
        plan = st.session_state.get("last_plan")
        if api and plan:
            st.markdown("##### Place the latest trade idea")
            sym = st.text_input("Broker trading symbol (exact, from the broker's contract list)")
            st.write(f"BUY {plan['qty']} x {plan['symbol']} limit ₹{plan['entry']:.2f}")
            sure = st.checkbox("I have verified the live price and symbol and want to place this real order")
            if st.button("🚀 Place real order", disabled=not (sure and sym)):
                ok, msg = shoonya_buy_limit(api, sym, plan["qty"], plan["entry"])
                (st.success if ok else st.error)(msg)


# ---------------------------------------------------------------- LEARN
def page_learn() -> None:
    hero("📚 Learn the basics", "Plain-English answers to the words you will see in this app.")
    items = {
        "What is an option? CALL vs PUT": "A **CALL (CE)** gains value when the index goes **up**. A **PUT (PE)** gains value when the index goes **down**. When you buy either, the most you can lose is the money you paid (the premium).",
        "Premium, lot and quantity": "**Premium** is the price per unit. A **lot** is a fixed bundle of units (e.g. NIFTY = 65). Cost of 1 lot = premium × lot size.",
        "Stop-loss and target": "**Stop-loss** is the price where you exit to cap your loss. **Target** is where you book profit. Decide both *before* you enter.",
        "Risk : Reward": "1 : 2 means you aim to make ₹2 for every ₹1 you risk. With that, you can be right only ~34% of the time and still break even.",
        "Why options lose value (theta)": "Every day an option loses a little value as expiry nears - fastest on expiry day. That is why you exit intraday and avoid holding to the close.",
        "Delta": "How much the option moves when the index moves 1 point. Delta 0.5 → ₹0.50 per index point. The app prefers strikes near 0.5.",
        "India VIX": "The market's 'fear gauge'. Higher VIX = more expensive options. The app uses it to estimate premiums.",
        "How are the signals made?": "Five simple checks: EMA 9 vs 21, price vs EMA 50, RSI, MACD and the last 3 candles. 3 or more points in one direction creates a CALL/PUT idea; otherwise WAIT.",
        "How accurate are the prices?": "Premiums are **estimates** from the Black-Scholes model using India VIX, because exchange option chains are not free. Real prices differ (skew, bid-ask, events). Always confirm in your broker app.",
    }
    for q, a in items.items():
        with st.expander(q):
            st.markdown(a)
    st.markdown(DISCLAIMER, unsafe_allow_html=True)
