import time
import logging
import schedule
import fmpsdk
import pandas as pd
import alpaca_trade_api as tradeapi
from alpaca_trade_api.common import URL
from config import (
    APCA_PAPER_API_BASE_URL,
    APCA_DATA_URL,
    APCA_PAPER_API_KEY,
    APCA_PAPER_API_SECRET,
)
from datetime import datetime

NY_TZ = "America/New_York"

# alpaca_api = tradeapi.REST(
#     APCA_PAPER_API_KEY, APCA_PAPER_API_SECRET, APCA_PAPER_API_BASE_URL, "v2"
# )

# start = pd.Timestamp("2021-02-19 9:00", tz=NY_TZ).isoformat()
# end = pd.Timestamp("2021-02-19 17:00", tz=NY_TZ).isoformat()
# print(alpaca_api.get_barset(["AAPL"], "minute", start=start, end=end).df)

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


# conn.run(["alpacadatav1/T.TSLA", "alpacadatav1/Q.TSLA", "alpacadatav1/AM.TSLA"])

watchlist = []


def fetch_earnings_job():

    global watchlist

    today = datetime.today().strftime("%Y-%m-%d")
    watchlist = fmpsdk.get_earning_calendar(today)


schedule.every().monday.at("12:05").do(fetch_earnings_job)
schedule.every().tuesday.at("12:05").do(fetch_earnings_job)
schedule.every().wednesday.at("12:05").do(fetch_earnings_job)
schedule.every().thursday.at("12:05").do(fetch_earnings_job)
schedule.every().friday.at("12:05").do(fetch_earnings_job)


while True:
    schedule.run_pending()
    time.sleep(1)