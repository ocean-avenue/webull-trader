import time
import threading
import schedule
import pytz
import yfsdk
import fmpsdk
from datetime import datetime

JOB_MAXIMUM = 20
JOB_INTERVAL = 60  # in second
INTRADAY_PERIOD = 50

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
    output_log = ""
    for top_quote in top_quotes:
        output_log += "{}, ${} ({} %). ".format(
            top_quote["symbol"],
            top_quote["price"],
            top_quote["changesPercentage"],
        )
        if top_quote["symbol"] not in watchlist:
            watchlist.append(top_quote["symbol"])
    print(
        "[{}] {} ({})".format(
            now,
            output_log,
            len(watchlist),
        )
    )

    if now.hour == 13:
        return schedule.CancelJob


def transaction_job(job_id):
    now = datetime.now()
    ny_tz = pytz.timezone("America/New_York")
    ny_now = now.astimezone(ny_tz)

    if job_id < len(watchlist):
        symbol = watchlist[job_id]
        intraday_sma = fmpsdk.get_intraday_sma(symbol, "1min", INTRADAY_PERIOD)
        # has enouth data
        if len(intraday_sma) >= 2:
            cur_sma = intraday_sma[0]
            cur_dt = datetime.strptime(cur_sma["date"], "%Y-%m-%d %H:%M:%S")
            # time not delayed
            if (
                ny_now.year == cur_dt.year
                and ny_now.day == cur_dt.day
                and ny_now.hour == cur_dt.hour
                and (ny_now.minute - cur_dt.minute) <= 1
            ):
                cur_price = cur_sma["close"]
                cur_smaval = cur_sma["sma"]

                pre_sma = intraday_sma[1]
                pre_price = pre_sma["close"]
                pre_smaval = pre_sma["sma"]

                if cur_price > cur_smaval and pre_price <= pre_smaval:
                    quote_short = fmpsdk.get_quote_short(symbol)
                    real_price = quote_short["price"]
                    print("[{}] * buy {}, ${} *".format(now, symbol, real_price))

                if cur_price < cur_smaval and pre_price >= pre_smaval:
                    quote_short = fmpsdk.get_quote_short(symbol)
                    real_price = quote_short["price"]
                    print("[{}] * sell {}, ${} *".format(now, symbol, real_price))

    if now.hour == 13:
        return schedule.CancelJob


def run_screening_thread():
    job_thread = threading.Thread(target=screening_job)
    job_thread.start()


def run_transaction_thread():
    for job_id in range(0, JOB_MAXIMUM):
        job_thread = threading.Thread(target=transaction_job, args=(job_id,))
        job_thread.start()


def start_trading_job():
    schedule.every(JOB_INTERVAL).seconds.do(run_screening_thread)
    schedule.every(JOB_INTERVAL).seconds.do(run_transaction_thread)


schedule.every().monday.at("06:30").do(start_trading_job)
schedule.every().tuesday.at("06:30").do(start_trading_job)
schedule.every().wednesday.at("06:30").do(start_trading_job)
schedule.every().thursday.at("06:30").do(start_trading_job)
schedule.every().friday.at("06:30").do(start_trading_job)

while True:
    schedule.run_pending()
    time.sleep(1)