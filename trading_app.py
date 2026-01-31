"""
Project: Binance Futures Testnet Trading Bot
Author: Akshita Kasera
Purpose: Internship Assignment Submission
"""

import streamlit as st
import time
import datetime
import logging
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException

# ---------- Logging setup ----------
logging.basicConfig(
    filename="akshita_trading_bot.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

# ---------- Streamlit page config ----------
st.set_page_config(
    page_title="Akshita Futures Trading Bot",
    layout="centered"
)

st.title("Akshita's Binance Futures Testnet Trading Bot")
st.caption("Python Developer Internship Assignment")

# ---------- Sidebar API input ----------
st.sidebar.header("🔐 Binance Testnet API")
api_key = st.sidebar.text_input("API Key")
api_secret = st.sidebar.text_input("API Secret", type="password")

client = None
symbols = []
account_info = {}

# ---------- Session order history ----------
if "order_history" not in st.session_state:
    st.session_state.order_history = []

# ---------- Connect to Binance ----------
if api_key and api_secret:
    try:
        client = Client(api_key, api_secret, testnet=True)
        client.FUTURES_URL = "https://testnet.binancefuture.com/fapi"

        # time sync
        server_time = client.get_server_time()
        local_time = int(time.time() * 1000)
        client.timestamp_offset = server_time['serverTime'] - local_time
        logging.info("Server time synchronized")

        # load symbols
        info = client.futures_exchange_info()
        symbols = [s["symbol"] for s in info["symbols"]]
        logging.info(f"Loaded {len(symbols)} trading symbols")

        # load balance
        try:
            balances = client.futures_account_balance()
            usdt_item = next((b for b in balances if b["asset"] == "USDT"), None)
            account_info["USDT_balance"] = usdt_item["balance"] if usdt_item else "N/A"
        except Exception as e:
            account_info["USDT_balance"] = "N/A"
            logging.warning(f"Balance fetch failed: {e}")

        st.sidebar.success("Connected to Binance Testnet")

    except Exception as e:
        st.sidebar.error(f"Connection failed: {e}")
        logging.error(f"API connection error: {e}")

# ---------- Main UI ----------
if symbols:
    col1, col2 = st.columns([3, 1])

    with col1:

        # default BTCUSDT if available
        default_symbol = "BTCUSDT" if "BTCUSDT" in symbols else symbols[0]
        symbol = st.selectbox(
            "Trading Symbol",
            symbols,
            index=symbols.index(default_symbol)
        )

        # live price
        try:
            ticker = client.futures_symbol_ticker(symbol=symbol)
            price_now = float(ticker["price"])
            st.markdown(f"### Live Price: $ {price_now:.6f}")
        except:
            st.markdown("### Live Price: unavailable")

        # ---------- Order Form ----------
        with st.form("trade_form"):

            order_type = st.selectbox("Order Type", ["MARKET", "LIMIT", "STOP"])
            side = st.radio("Trade Side", ["BUY", "SELL"])
            quantity = st.number_input("Quantity", min_value=0.0001, value=0.01, format="%.6f")

            price = None
            stop_price = None

            if order_type in ("LIMIT", "STOP"):
                price = st.number_input("Limit Price", min_value=0.0, format="%.6f")

            if order_type == "STOP":
                stop_price = st.number_input("Stop Trigger Price", min_value=0.0, format="%.6f")

            submitted = st.form_submit_button("🚀 Execute Order")

        # ---------- On Submit ----------
        if submitted:

            st.warning("Please verify order details before execution")

            params = {
                "symbol": symbol,
                "side": SIDE_BUY if side == "BUY" else SIDE_SELL,
                "quantity": quantity,
                "type": None,
                "recvWindow": 5000
            }

            errors = []

            if quantity <= 0:
                errors.append("Quantity must be positive")

            if order_type == "MARKET":
                params["type"] = ORDER_TYPE_MARKET

            elif order_type == "LIMIT":
                if not price or price <= 0:
                    errors.append("Valid limit price required")
                else:
                    params.update(
                        type=ORDER_TYPE_LIMIT,
                        price=price,
                        timeInForce=TIME_IN_FORCE_GTC
                    )

            elif order_type == "STOP":
                if not price or price <= 0:
                    errors.append("Limit price required")
                if not stop_price or stop_price <= 0:
                    errors.append("Stop trigger price required")
                if not errors:
                    params.update(
                        type=ORDER_TYPE_STOP,
                        price=price,
                        stopPrice=stop_price,
                        timeInForce=TIME_IN_FORCE_GTC
                    )

            # ---------- Error Display ----------
            if errors:
                for e in errors:
                    st.error(e)
                    logging.warning(f"Validation error: {e}")

            else:
                try:
                    logging.info(f"Order attempt — {side} {quantity} {symbol} ({order_type})")
                    order = client.futures_create_order(**params)

                    st.success(f"Order submitted! ID: {order.get('orderId')}")

                    st.json(order)

                    st.session_state.order_history.append({
                        "time": datetime.datetime.now().strftime("%H:%M:%S"),
                        "symbol": order.get("symbol"),
                        "side": order.get("side"),
                        "type": order.get("type"),
                        "status": order.get("status"),
                        "qty": order.get("origQty"),
                    })

                except BinanceAPIException as e:
                    st.error(f"Exchange error: {e.message}")
                    logging.error(e.message)

                except Exception as e:
                    st.error(f"Unexpected error: {e}")
                    logging.error(e)

    # ---------- Side Panel ----------
    with col2:
        st.markdown("### Account")
        st.metric("USDT Balance", account_info.get("USDT_balance", "N/A"))

    # ---------- Order History ----------
    if st.session_state.order_history:
        st.subheader("Recent Orders")
        for o in reversed(st.session_state.order_history):
            st.write(o)

else:
    st.info("Enter Binance Testnet API keys in sidebar to begin")

# ---------- Footer ----------
st.markdown("---")
st.caption("Developed by Akshita Kasera • Internship Assignment Project")
