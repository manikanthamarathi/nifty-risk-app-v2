"""Optional: Shoonya (Finvasia) broker login/orders and Telegram alerts.

Credentials are never stored on disk - they live only in st.session_state for the current browser session.
NOTE: broker functions need a real Shoonya account and could not be tested without one.
"""
from __future__ import annotations

import requests


def telegram_send(token: str, chat_id: str, text: str) -> tuple[bool, str]:
    try:
        r = requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                          json={"chat_id": chat_id, "text": text}, timeout=10)
        if r.ok:
            return True, "Message sent."
        return False, f"Telegram said: {r.json().get('description', r.status_code)}"
    except Exception as e:  # network, bad token format, etc.
        return False, f"Could not reach Telegram: {e}"


def shoonya_login(user_id: str, password: str, factor2: str, vendor_code: str, api_secret: str, imei: str = "indicerisk"):
    """Returns (api_object_or_None, message)."""
    try:
        from NorenRestApiPy.NorenApi import NorenApi
    except Exception as e:
        return None, f"Broker library could not load: {e!r}"

    class _Api(NorenApi):
        def __init__(self):
            super().__init__(host="https://api.shoonya.com/NorenWClientTP/", websocket="wss://api.shoonya.com/NorenWSTP/")

    api = _Api()
    try:
        res = api.login(userid=user_id, password=password, twoFA=factor2, vendor_code=vendor_code,
                        api_secret=api_secret, imei=imei)
    except Exception as e:
        return None, f"Login failed: {e}"
    if res and res.get("stat") == "Ok":
        return api, f"Connected as {res.get('uname', user_id)}."
    return None, f"Login failed: {(res or {}).get('emsg', 'no response from broker')}"


def shoonya_buy_limit(api, tradingsymbol: str, qty: int, price: float, exchange: str = "NFO"):
    """Places a BUY limit order (intraday). tradingsymbol must be the broker's exact symbol."""
    try:
        res = api.place_order(buy_or_sell="B", product_type="I", exchange=exchange, tradingsymbol=tradingsymbol,
                              quantity=int(qty), discloseqty=0, price_type="LMT", price=float(price),
                              trigger_price=None, retention="DAY", remarks="IndiceRisk")
    except Exception as e:
        return False, f"Order failed: {e}"
    if res and res.get("stat") == "Ok":
        return True, f"Order placed. Order number: {res.get('norenordno')}"
    return False, f"Broker rejected the order: {(res or {}).get('emsg', 'no response')}"
