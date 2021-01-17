import time
import threading
import schedule
import pytz
import logging
import yfsdk
import fmpsdk
from datetime import datetime


watchlist = []
positions = []


def screening_job():
    now = datetime.now()
    most_gainers = yfsdk.get_most_gainers()
    # pick highest acceleration
    symbol_list = []
    for most_gainer in most_gainers:
        symbol = most_gainer["symbol"]
        symbol_list.append(symbol)
    quotes = fmpsdk.get_quotes(symbol_list)
    # fill quote acceleration
    for quote in quotes:
        price = quote["price"]
        open_price = quote["open"]
        quote["acceleration"] = (price - open_price) / open_price
    # sort quote based on price acceleration
    quotes.sort(key=lambda x: x["acceleration"], reverse=True)
    top_quotes = quotes[:3]
    for top_quote in top_quotes:
        logging.info(
            "[{}] {}, ${} ({}%)".format(
                now,
                top_quote["symbol"],
                top_quote["price"],
                top_quote["changesPercentage"],
            )
        )
        if top_quote["symbol"] not in watchlist:
            watchlist.append(top_quote["symbol"])

    if now.hour == 13:
        return schedule.CancelJob


def transaction_job():
    now = datetime.now()

    for symbol in watchlist:
        intraday_sma = fmpsdk.get_intraday_sma(symbol, "1min")
        if len(intraday_sma) < 2:
            continue
        cur_sma = intraday_sma[0]
        pre_sma = intraday_sma[1]
        # TODO

    if now.hour == 13:
        return schedule.CancelJob


def run_threaded(job_func):
    job_thread = threading.Thread(target=job_func)
    job_thread.start()


def start_trading_job():
    schedule.every(60).seconds.do(run_threaded, transaction_job)
    schedule.every(60).seconds.do(run_threaded, screening_job)


schedule.every().monday.at("06:30").do(start_trading_job)
schedule.every().tuesday.at("06:30").do(start_trading_job)
schedule.every().wednesday.at("06:30").do(start_trading_job)
schedule.every().thursday.at("06:30").do(start_trading_job)
schedule.every().friday.at("06:30").do(start_trading_job)


while True:
    schedule.run_pending()
    time.sleep(1)