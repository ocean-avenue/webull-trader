import time

import schedule
from datetime import datetime, timedelta
from sdk import fmpsdk

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
# FETCH_EARNINGS_TIME = "00:05"  # local time (sf)
FETCH_EARNINGS_TIME = "08:05"  # utc time (aws ec2)
schedule.every().monday.at(FETCH_EARNINGS_TIME).do(fetch_earnings_job)
schedule.every().tuesday.at(FETCH_EARNINGS_TIME).do(fetch_earnings_job)
schedule.every().wednesday.at(FETCH_EARNINGS_TIME).do(fetch_earnings_job)
schedule.every().thursday.at(FETCH_EARNINGS_TIME).do(fetch_earnings_job)
schedule.every().friday.at(FETCH_EARNINGS_TIME).do(fetch_earnings_job)


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
# START_TRADE_TIME = "06:35"  # local time (sf)
START_TRADE_TIME = "14:35"  # utc time (aws ec2)
schedule.every().monday.at(START_TRADE_TIME).do(start_trade_job)
schedule.every().tuesday.at(START_TRADE_TIME).do(start_trade_job)
schedule.every().wednesday.at(START_TRADE_TIME).do(start_trade_job)
schedule.every().thursday.at(START_TRADE_TIME).do(start_trade_job)
schedule.every().friday.at(START_TRADE_TIME).do(start_trade_job)


while True:
    schedule.run_pending()
    time.sleep(1)