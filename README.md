# IndiceRisk Pro

Free, beginner-friendly assistant for NIFTY / BANKNIFTY / FINNIFTY / SENSEX option buying.
Pick an index + budget -> get the option, entry, stop-loss, target and lots. Paper trading first.

## Run
    pip install -r requirements.txt
    streamlit run app.py

## Notes
- Data: free Yahoo Finance feed (delayed). If unreachable, the app shows clearly-labelled DEMO data.
- Option premiums are Black-Scholes estimates using India VIX (exchange option chains are not free). Always verify in your broker app.
- Lot sizes / strike gaps / expiry dates are editable under "Advanced" - confirm current values on NSE/BSE.
- Credentials (Telegram, Shoonya) are kept in session memory only. Never commit them to git.
- Educational tool, not investment advice.
