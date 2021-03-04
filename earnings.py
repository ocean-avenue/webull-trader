import time

# import logging
import schedule
import fmpsdk
from alpaca_trade_api.stream import Stream
from alpaca_trade_api.common import URL
from config import (
    APCA_PAPER_API_BASE_URL,
    APCA_PAPER_API_KEY,
    APCA_PAPER_API_SECRET,
)
from datetime import datetime

# NY_TZ = "America/New_York"

# logging.basicConfig(level=logging.INFO)
stream = Stream(
    APCA_PAPER_API_KEY,
    APCA_PAPER_API_SECRET,
    base_url=URL(APCA_PAPER_API_BASE_URL),
    data_feed="iex",  # <- replace to SIP if you have PRO subscription
)

stream.run()

watchlist = []


async def print_trade(t):
    print("trade", t)


def subscribe_trades_job():

    global watchlist

    limit_watchlist = watchlist[0:30]
    for earning_stock in limit_watchlist:
        symbol = earning_stock["symbol"]
        print("subscribe to {} trades".format(symbol))
        stream.subscribe_trades(print_trade, symbol)


def unsubscribe_trades_job():

    global watchlist

    limit_watchlist = watchlist[0:30]
    for earning_stock in limit_watchlist:
        symbol = earning_stock["symbol"]
        print("unsubscribe to {} trades".format(symbol))
        stream.unsubscribe_trades(symbol)


schedule.every().monday.at("01:00").do(subscribe_trades_job)
schedule.every().tuesday.at("01:00").do(subscribe_trades_job)
schedule.every().wednesday.at("01:00").do(subscribe_trades_job)
schedule.every().thursday.at("01:00").do(subscribe_trades_job)
schedule.every().friday.at("01:00").do(subscribe_trades_job)

schedule.every().monday.at("17:00").do(unsubscribe_trades_job)
schedule.every().tuesday.at("17:00").do(unsubscribe_trades_job)
schedule.every().wednesday.at("17:00").do(unsubscribe_trades_job)
schedule.every().thursday.at("17:00").do(unsubscribe_trades_job)
schedule.every().friday.at("17:00").do(unsubscribe_trades_job)


def fetch_earnings_job():

    global watchlist

    today = datetime.today().strftime("%Y-%m-%d")
    watchlist = fmpsdk.get_earning_calendar(today)

    print("fetch {} earnings".format(len(watchlist)))


schedule.every().monday.at("00:05").do(fetch_earnings_job)
schedule.every().tuesday.at("00:05").do(fetch_earnings_job)
schedule.every().wednesday.at("00:05").do(fetch_earnings_job)
schedule.every().thursday.at("00:05").do(fetch_earnings_job)
schedule.every().friday.at("00:05").do(fetch_earnings_job)

while True:
    schedule.run_pending()
    time.sleep(1)