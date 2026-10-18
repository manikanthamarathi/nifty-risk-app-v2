import streamlit as st

from core.data import market_status
from ui.pages import page_connect, page_home, page_learn, page_ledger, page_paper, page_risk, page_trade
from ui.styles import inject_css, pill

st.set_page_config(page_title="IndiceRisk Pro", page_icon="⚡", layout="wide")
inject_css()

PAGES = {
    "🏠 Start Here": page_home,
    "🎯 Trade Ideas": page_trade,
    "🛡️ Risk Calculator": page_risk,
    "📝 Paper Trading": page_paper,
    "📊 P&L Ledger": page_ledger,
    "🔗 Broker & Alerts": page_connect,
    "📚 Learn": page_learn,
}

with st.sidebar:
    st.markdown("## ⚡ IndiceRisk Pro")
    st.radio("Go to", list(PAGES), key="nav", label_visibility="collapsed")
    ok, msg = market_status()
    st.markdown(pill(msg, "green" if ok else "red"), unsafe_allow_html=True)
    st.caption("Free • Paper-trading first • Not investment advice")

PAGES[st.session_state.get("nav", "🏠 Start Here")]()
