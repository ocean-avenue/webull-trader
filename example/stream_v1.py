import logging
import pandas as pd
import alpaca_trade_api as tradeapi
from alpaca_trade_api.common import URL

APCA_DATA_URL = "https://data.alpaca.markets"
APCA_PAPER_API_BASE_URL = "https://paper-api.alpaca.markets"
APCA_PAPER_API_KEY = "PKXWBBJ7M52WIZUJGVNL"
APCA_PAPER_API_SECRET = "uBIZAHUqflUVx0qwaJ6wsghxpyfORFLSMpdmuSHI"

NY_TZ = "America/New_York"

logging.basicConfig(format="%(asctime)s %(message)s", level=logging.INFO)
conn = tradeapi.StreamConn(
    APCA_PAPER_API_KEY,
    APCA_PAPER_API_SECRET,
    base_url=URL(APCA_PAPER_API_BASE_URL),
    data_url=URL(APCA_DATA_URL),
    data_stream="alpacadatav1",
)


@conn.on(r"^AM\..+$")
async def on_minute_bars(conn, channel, bar):
    print("bars", bar)


quote_count = 0  # don't print too much quotes


@conn.on(r"Q\..+")
async def on_quotes(conn, channel, quote):
    global quote_count
    if quote_count % 10 == 0:
        print("quote", quote)
    quote_count += 1


@conn.on(r"T\..+")
async def on_trades(conn, channel, trade):
    print("trade", trade)


conn.run(["alpacadatav1/T.SQ", "alpacadatav1/Q.TSLA", "alpacadatav1/AM.PLUG"])