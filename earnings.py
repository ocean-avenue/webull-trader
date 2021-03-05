import time

import schedule
import fmpsdk
from datetime import datetime, timedelta

# NY_TZ = "America/New_York"
CHANGE_THRESHOLD = 0.04

watchlist = []


def fetch_earnings_job():

    global watchlist

    today = datetime.today().strftime("%Y-%m-%d")
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    watchlist = fmpsdk.get_earning_calendar(yesterday, today)

    print("fetch {} earnings".format(len(watchlist)))


# fetch earning at every midnight
schedule.every().monday.at("00:05").do(fetch_earnings_job)
schedule.every().tuesday.at("00:05").do(fetch_earnings_job)
schedule.every().wednesday.at("00:05").do(fetch_earnings_job)
schedule.every().thursday.at("00:05").do(fetch_earnings_job)
schedule.every().friday.at("00:05").do(fetch_earnings_job)


def start_trade_job():

    global watchlist

    today = datetime.today().strftime("%Y-%m-%d")
    yesterday = (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d")

    earning_list = []
    symbol_list = []
    # filter out valid earning list
    for earning in watchlist:
        if earning["date"] == today and earning["time"] == "bmo":  # before market open
            earning_list.append(earning)
            symbol_list.append(earning["symbol"])
        elif (
            earning["date"] == yesterday and earning["time"] == "amc"
        ):  # after market close
            earning_list.append(earning)
            symbol_list.append(earning["symbol"])

    quotes = fmpsdk.get_quotes(symbol_list)
    for quote in quotes:
        symbol = quote["symbol"]
        last_price = quote["price"]
        open_price = quote["open"]
        changes_percentage = quote["changesPercentage"]
        if changes_percentage >= CHANGE_THRESHOLD * 100 and last_price >= open_price:
            print("[{}] buy @ ${}".format(symbol, last_price))


# start trade job at every morning
schedule.every().monday.at("06:35").do(start_trade_job)
schedule.every().tuesday.at("06:35").do(start_trade_job)
schedule.every().wednesday.at("06:35").do(start_trade_job)
schedule.every().thursday.at("06:35").do(start_trade_job)
schedule.every().friday.at("06:35").do(start_trade_job)


while True:
    schedule.run_pending()
    time.sleep(1)