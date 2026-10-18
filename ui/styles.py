"""CSS + small HTML helpers. All HTML is built without leading indentation so Markdown never treats it as code."""
import streamlit as st

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: radial-gradient(900px 500px at 8% -8%, rgba(99,102,241,.18), transparent 60%),
                     radial-gradient(800px 500px at 100% 0%, rgba(34,197,94,.10), transparent 55%), #0b1020; }
#MainMenu, footer { visibility: hidden; }
.block-container { padding-top: 1.6rem; max-width: 1180px; }

@keyframes fadeUp { from { opacity: 0; transform: translateY(16px); } to { opacity: 1; transform: none; } }
@keyframes pulse { 0% { box-shadow: 0 0 0 0 rgba(34,197,94,.65); } 70% { box-shadow: 0 0 0 10px rgba(34,197,94,0); } 100% { box-shadow: 0 0 0 0 rgba(34,197,94,0); } }
@keyframes pulseRed { 0% { box-shadow: 0 0 0 0 rgba(239,68,68,.55); } 70% { box-shadow: 0 0 0 10px rgba(239,68,68,0); } 100% { box-shadow: 0 0 0 0 rgba(239,68,68,0); } }
@keyframes shift { 0% { background-position: 0% 50%; } 50% { background-position: 100% 50%; } 100% { background-position: 0% 50%; } }
@keyframes grow { from { width: 0; } to { width: var(--w); } }
@keyframes float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-5px); } }

.hero { padding: 26px 28px; border-radius: 20px; margin-bottom: 18px; color: #fff; animation: fadeUp .6s both;
        background: linear-gradient(120deg, #4f46e5, #7c3aed, #0ea5e9, #4f46e5); background-size: 300% 300%; animation: fadeUp .6s both, shift 12s ease infinite; }
.hero h1 { margin: 0 0 6px 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -.5px; }
.hero p { margin: 0; opacity: .92; font-size: 1.02rem; }

.card { background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.09); border-radius: 18px; padding: 20px 22px;
        margin-bottom: 14px; animation: fadeUp .6s both; backdrop-filter: blur(6px); transition: transform .2s, border-color .2s; }
.card:hover { transform: translateY(-3px); border-color: rgba(129,140,248,.55); }
.card h3 { margin: 0 0 8px 0; font-size: 1.05rem; }
.card p { margin: 0; color: #b6bfdc; font-size: .93rem; line-height: 1.5; }
.step-no { display: inline-flex; width: 30px; height: 30px; border-radius: 50%; align-items: center; justify-content: center;
           background: linear-gradient(135deg, #6366f1, #a855f7); font-weight: 800; margin-bottom: 10px; animation: float 3s ease-in-out infinite; }

.pill { display: inline-flex; align-items: center; gap: 8px; padding: 6px 14px; border-radius: 999px; font-size: .82rem; font-weight: 600;
        margin: 0 8px 8px 0; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.1); }
.dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; }
.dot.green { background: #22c55e; animation: pulse 1.8s infinite; }
.dot.red { background: #ef4444; animation: pulseRed 1.8s infinite; }
.dot.amber { background: #f59e0b; }

.signal { border-radius: 20px; padding: 22px 24px; margin-bottom: 14px; animation: fadeUp .6s both; border: 1px solid; }
.signal.call { background: linear-gradient(135deg, rgba(34,197,94,.20), rgba(34,197,94,.05)); border-color: rgba(34,197,94,.5); }
.signal.put { background: linear-gradient(135deg, rgba(239,68,68,.20), rgba(239,68,68,.05)); border-color: rgba(239,68,68,.5); }
.signal.wait { background: linear-gradient(135deg, rgba(245,158,11,.18), rgba(245,158,11,.04)); border-color: rgba(245,158,11,.5); }
.signal .big { font-size: 1.7rem; font-weight: 800; letter-spacing: -.5px; }
.signal .sub { color: #c4cbe6; font-size: .95rem; margin-top: 4px; }

.meter { height: 10px; border-radius: 99px; background: rgba(255,255,255,.1); overflow: hidden; margin-top: 12px; }
.meter > div { height: 100%; border-radius: 99px; width: var(--w); animation: grow 1.2s ease-out both; }
.meter .green { background: linear-gradient(90deg, #16a34a, #4ade80); }
.meter .red { background: linear-gradient(90deg, #dc2626, #f87171); }
.meter .amber { background: linear-gradient(90deg, #d97706, #fbbf24); }

.trade { border-radius: 22px; padding: 24px; margin: 6px 0 16px 0; animation: fadeUp .7s both; border: 1px solid rgba(129,140,248,.45);
         background: linear-gradient(135deg, rgba(79,70,229,.25), rgba(14,165,233,.10)); }
.trade .head { font-size: 1.5rem; font-weight: 800; }
.trade .tag { font-size: .8rem; color: #a5b4fc; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 700; }

.tile { border-radius: 16px; padding: 16px 18px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.09);
        animation: fadeUp .7s both; transition: transform .2s; height: 100%; }
.tile:hover { transform: translateY(-3px); }
.tile .tl { font-size: .74rem; text-transform: uppercase; letter-spacing: 1.2px; color: #93a0cc; font-weight: 600; }
.tile .tv { font-size: 1.55rem; font-weight: 800; margin-top: 4px; }
.tile .ts { font-size: .8rem; color: #93a0cc; margin-top: 2px; }
.tile.good { border-color: rgba(34,197,94,.45); } .tile.good .tv { color: #4ade80; }
.tile.bad { border-color: rgba(239,68,68,.45); } .tile.bad .tv { color: #f87171; }
.tile.info .tv { color: #a5b4fc; }

.reason { padding: 8px 12px; border-radius: 10px; margin-bottom: 6px; font-size: .9rem; background: rgba(255,255,255,.04); animation: fadeUp .5s both; }
.reason.bull { border-left: 3px solid #22c55e; } .reason.bear { border-left: 3px solid #ef4444; } .reason.warn { border-left: 3px solid #f59e0b; }

.disclaimer { font-size: .78rem; color: #8590b8; border-top: 1px solid rgba(255,255,255,.08); padding-top: 12px; margin-top: 26px; line-height: 1.5; }
.stButton > button { border-radius: 12px; font-weight: 700; transition: transform .15s, box-shadow .15s; }
.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 22px rgba(99,102,241,.35); }
[data-testid="stSidebar"] { border-right: 1px solid rgba(255,255,255,.07); }
</style>
"""


def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title: str, sub: str) -> None:
    st.markdown(f'<div class="hero"><h1>{title}</h1><p>{sub}</p></div>', unsafe_allow_html=True)


def pill(text: str, dot: str = "") -> str:
    d = f'<span class="dot {dot}"></span>' if dot else ""
    return f'<span class="pill">{d}{text}</span>'


def pills(*items: str) -> None:
    st.markdown("".join(items), unsafe_allow_html=True)


def card(title: str, body: str, step: str = "") -> str:
    s = f'<div class="step-no">{step}</div>' if step else ""
    return f'<div class="card">{s}<h3>{title}</h3><p>{body}</p></div>'


def tile(label: str, value: str, sub: str = "", kind: str = "info") -> str:
    return f'<div class="tile {kind}"><div class="tl">{label}</div><div class="tv">{value}</div><div class="ts">{sub}</div></div>'


def meter(value: int, colour: str) -> str:
    return f'<div class="meter"><div class="{colour}" style="--w:{value}%"></div></div>'


def inr(x: float, dec: int = 0) -> str:
    return f"₹{x:,.{dec}f}"


DISCLAIMER = ('<div class="disclaimer">⚠️ <b>Educational tool - not investment advice.</b> Signals come from simple indicators and can be wrong. '
              'Option prices here are <b>model estimates</b> (Black-Scholes using India VIX), not live exchange quotes - always check the real '
              'premium in your broker app before trading. Buying options can lose 100% of the premium. Start with paper trading. '
              'The author is not a SEBI-registered adviser.</div>')
