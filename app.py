# 👇 DIT IS DE BEGIN VAN JE CODE
import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="EMA10/100 Backtester", layout="wide")
st.title("📈 EMA10/100 Backtest Tool")

symbol = st.text_input("Ticker symbool", value="PG")
interval = st.selectbox("Interval", ["1h", "2h", "4h", "1d"], index=2)
start_date = st.date_input("Startdatum", pd.to_datetime("2024-11-01"))
end_date = st.date_input("Einddatum", pd.to_datetime("2025-07-01"))
portfolio_size = st.number_input("Portfoliowaarde ($)", value=10_000)

risk_pct = st.slider("Risico per trade (%)", 0.5, 5.0, 2.0) / 100
sl_pct = st.slider("Stoploss onder entry (%)", 1.0, 10.0, 5.0) / 100
use_sl = st.checkbox("Gebruik Stoploss", value=True)

use_trailing_pct = st.checkbox("Trailing SL als percentage", value=True)
trailing_pct = st.slider("Trailing stop %", 1.0, 10.0, 4.0) / 100
trailing_ema = st.slider("Trailing EMA periode", 10, 100, 50)

max_rr = st.slider("Maximale R:R", 1.0, 10.0, 7.0)
fee_pct = st.number_input("Percentage fee (%)", value=0.002)
fee_fixed = st.number_input("Vaste fee ($)", value=2.5)

run = st.button("✅ Start backtest")

if run:
    data = yf.download(tickers=symbol, start=start_date, end=end_date, interval=interval)
    data.dropna(inplace=True)
    data["EMA10"] = data["Close"].ewm(span=10).mean()
    data["EMA100"] = data["Close"].ewm(span=100).mean()
    data[f"EMA{trailing_ema}"] = data["Close"].ewm(span=trailing_ema).mean()
    data["Signal"] = (data["EMA10"] > data["EMA100"]) & (data["EMA10"].shift(1) <= data["EMA100"].shift(1))

    trades = []
    in_trade = False

    for i in range(1, len(data)):
        if data["Signal"].iloc[i] and not in_trade:
            entry = data["Close"].iloc[i].item()
            sl = entry * (1 - sl_pct) if use_sl else None
            stop = entry - sl if use_sl else 1.0
            size = (portfolio_size * risk_pct) / stop
            trail = entry * (1 - trailing_pct) if use_trailing_pct else data[f"EMA{trailing_ema}"].iloc[i]
            max_price = entry
            entry_time = data.index[i]
            in_trade = True

        elif in_trade:
            price = data["Close"].iloc[i].item()
            max_price = max(max_price, price)
            trail = max_price * (1 - trailing_pct) if use_trailing_pct else max(trail, data[f"EMA{trailing_ema}"].iloc[i])
            rr = (max_price - entry) / (entry - sl) if use_sl else 0
            gross = (price - entry) * size
            value = size * entry
            fee = value * fee_pct + fee_fixed
            net = gross - fee

            reason = None
            if use_sl and price <= sl:
                reason = "SL"
            elif price <= trail:
                reason = "Trailing"
            elif rr >= max_rr:
                reason = "RR Target"

            if reason:
                trades.append({
                    "Entry Time": entry_time,
                    "Exit Time": data.index[i],
                    "Entry": round(entry, 2),
                    "Exit": round(price, 2),
                    "Result ($)": round(net, 2),
                    "Exit Type": reason
                })
                in_trade = False

    df = pd.DataFrame(trades)
    st.subheader("📊 Resultaten")
    st.dataframe(df)

    if not df.empty:
        st.markdown(f"**Trades:** {len(df)}")
        st.markdown(f"**Netto Winst:** ${df['Result ($)'].sum():.2f}")
        st.markdown(f"**Winrate:** {100 * (df['Result ($)'] > 0).mean():.2f}%")

    st.subheader("📉 Grafiek")
    fig, ax = plt.subplots(figsize=(14, 5))
    ax.plot(data["Close"], label="Close", alpha=0.6)
    ax.plot(data["EMA10"], label="EMA10", linestyle="--")
    ax.plot(data["EMA100"], label="EMA100", linestyle="--")
    ax.plot(data[f"EMA{trailing_ema}"], label=f"EMA{trailing_ema}", linestyle=":")
    ax.legend()
    st.pyplot(fig)
