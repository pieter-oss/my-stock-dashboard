# my_valuation_dashboard.py
import streamlit as st
import pandas as pd
import requests
from datetime import datetime

st.set_page_config(page_title="My 20-Stock Valuation Dashboard", layout="wide")
st.title("My Personal 20-Year EV/EBITDA & P/S Watchlist")
st.markdown("**Green cells** = currently cheaper than 20-year historical average")

# ==================== YOUR FREE API KEY ====================
FMP_KEY = "g4ZuHAQ1NJMzQXnSc6ALNTEsKjxJS0gC"   # ← your key is correct!

if FMP_KEY == "YOUR_FMP_KEY_HERE":
    st.error("Please get your free FMP API key and paste it in the code (line above)")
    st.stop()

# ==================== CUSTOM WATCHLIST INPUT ====================
st.sidebar.header("My Watchlist (max 30 symbols)")
default_list = "AAPL MSFT GOOGL AMZN NVDA TSLA META BRK-B JNJ JPM V PG UNH HD MA DIS NFLX ADBE PYPL"

user_input = st.sidebar.text_area(
    "Enter your tickers (space or comma separated)",
    value=st.session_state.get("my_tickers", default_list),
    height=150,
    help="Example: AAPL MSFT TSLA NVDA KO"
)

raw_tickers = [x.strip().upper() for x in user_input.replace(",", " ").split() if x.strip()]
MY_TICKERS = list(dict.fromkeys(raw_tickers))[:30]
st.session_state.my_tickers = " ".join(MY_TICKERS)
st.sidebar.success(f"Tracking {len(MY_TICKERS)} stocks")

# ==================== FETCH CURRENT RATIOS ====================
@st.cache_data(ttl=3600, show_spinner=False)
def get_current_ratios(tickers):
    rows = []
    for symbol in tickers:
        try:
            import yfinance as yf
            info = yf.Ticker(symbol).info
            ev = info.get("enterpriseToEbitda")
            ps = info.get("priceToSalesTrailing12Months")
            name = info.get("longName", symbol)

            if ev is None or ps is None:
                url = f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/{symbol}?apikey={FMP_KEY}"
                data = requests.get(url, timeout=10).json()
                if data:
                    if ev is None:
                        ev = data[0].get("enterpriseValueOverEBITDATTM")
                    if ps is None:
                        ps = data[0].get("priceToSalesRatioTTM")

            rows.append({
                "Symbol": symbol,
                "Company": name,
                "EV/EBITDA": round(ev, 2) if ev else None,
                "P/S": round(ps, 2) if ps else None,
            })
        except:
            rows.append({"Symbol": symbol, "Company": symbol, "EV/EBITDA": None, "P/S": None})
    return pd.DataFrame(rows)

# ==================== 20-YEAR HISTORICAL AVERAGES ====================
@st.cache_data(ttl=86400, show_spinner=False)
def get_20y_averages(tickers):
    rows = []
    url_base = "https://financialmodelingprep.com/api/v3/key-metrics/"
    for symbol in tickers:
        try:
            url = f"{url_base}{symbol}?period=annual&limit=40&apikey={FMP_KEY}"
            yearly = requests.get(url, timeout=10).json()
            if not yearly:
                rows.append({"Symbol": symbol, "20Y Avg EV/EBITDA": None, "20Y Avg P/S": None, "Years": 0})
                continue

            df = pd.DataFrame(yearly)
            df["ev"] = pd.to_numeric(df["enterpriseValueOverEBITDA"], errors="coerce")
            df["ps"] = pd.to_numeric(df["priceToSalesRatio"], errors="coerce")
            recent_20 = df.head(20)
            years_available = len(recent_20.dropna(subset=["ev", "ps"]))

            rows.append({
                "Symbol": symbol,
                "20Y Avg EV/EBITDA": round(recent_20["ev"].mean(), 2),
                "20Y Avg P/S": round(recent_20["ps"].mean(), 2),
                "Years": years_available
            })
        except:
            rows.append({"Symbol": symbol, "20Y Avg EV/EBITDA": None, "20Y Avg P/S": None, "Years": 0})
    return pd.DataFrame(rows)

# ==================== LOAD AND MERGE ====================
with st.spinner("Loading current ratios..."):
    current_df = get_current_ratios(MY_TICKERS)

with st.spinner("Calculating 20-year historical averages..."):
    hist_df = get_20y_averages(MY_TICKERS)

df = current_df.merge(hist_df, on="Symbol")

# ==================== HIGHLIGHTING ====================
def highlight(row):
    styles = [""] * len(row)
    if pd.notna(row["EV/EBITDA"]) and pd.notna(row["20Y Avg EV/EBITDA"]):
        if row["EV/EBITDA"] < row["20Y Avg EV/EBITDA"]:
            styles[2] = "background-color: #90EE90; font-weight: bold; color: black"
    if pd.notna(row["P/S"]) and pd.notna(row["20Y Avg P/S"]):
        if row["P/S"] < row["20Y Avg P/S"]:
            styles[3] = "background-color: #90EE90; font-weight: bold; color: black"
    return styles

styled = df.style.apply(highlight, axis=1).format({
    "EV/EBITDA": "{:.2f}", "20Y Avg EV/EBITDA": "{:.2f}",
    "P/S": "{:.2f}", "20Y Avg P/S": "{:.2f}"
}, na_rep="—").set_properties(**{"text-align": "center"}, subset=["EV/EBITDA","20Y Avg EV/EBITDA","P/S","20Y Avg P/S"])

st.dataframe(styled, use_container_width=True, height=900)

cheap = df[((df["EV/EBITDA"] < df["20Y Avg EV/EBITDA"]) | (df["P/S"] < df["20Y Avg P/S"]))]
st.success(f"**{len(cheap)} out of {len(df)}** stocks are currently below their 20-year average on at least one metric")

st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M')} • Free data via Financial Modeling Prep")

