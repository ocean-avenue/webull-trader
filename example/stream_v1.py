import logging
import pandas as pd
from datetime import datetime
import alpaca_trade_api as tradeapi
from alpaca_trade_api.common import URL

from sdk.config import (
    APCA_DATA_URL,
    APCA_PAPER_API_BASE_URL,
    APCA_PAPER_API_KEY,
    APCA_PAPER_API_SECRET,
)

# NY_TZ = "America/New_York"

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
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "bars", bar)


quote_count = 0  # don't print too much quotes


@conn.on(r"Q\..+")
async def on_quotes(conn, channel, quote):
    global quote_count
    if quote_count % 10 == 0:
        print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "quote", quote)
    quote_count += 1


@conn.on(r"T\..+")
async def on_trades(conn, channel, trade):
    print(datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "trade", trade)


conn.run(["alpacadatav1/T.SQ", "alpacadatav1/Q.TSLA", "alpacadatav1/AM.PLUG"])