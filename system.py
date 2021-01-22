import time
import threading
import schedule
import logging
import pytz
import yfsdk
import fmpsdk
from datetime import datetime

JOB_MAXIMUM = 20
JOB_INTERVAL = 60  # in second
INTRADAY_PERIOD = 50

watchlist = []
positions = []


def print_log(now, msg):
    print("[{}] {}".format(now.strftime("%Y-%m-%d %H:%M:%S"), msg))


def screening_job():
    now = datetime.now()
    ny_tz = pytz.timezone("America/New_York")
    ny_now = now.astimezone(ny_tz)

    try:
        most_gainers = yfsdk.get_most_gainers()
        # pick highest acceleration
        symbol_list = []
        gainers_log = ""
        for most_gainer in most_gainers:
            symbol = most_gainer["symbol"]
            change_percentage = most_gainer["change_percentage"]
            symbol_list.append(symbol)
            gainers_log += "{} {}, ".format(symbol, change_percentage)
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
            if top_quote["symbol"] not in watchlist:
                watchlist.append(top_quote["symbol"])
        print_log(ny_now, "watchlist: {}".format(watchlist))
        # write most gainers log
        logging.info(gainers_log)
    except:
        print_log(ny_now, "screen job failed")

    if now.hour == 13:
        return schedule.CancelJob


def transaction_job(job_id):
    now = datetime.now()
    ny_tz = pytz.timezone("America/New_York")
    ny_now = now.astimezone(ny_tz)

    try:
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

                    # buy signal
                    if cur_price > cur_smaval and pre_price <= pre_smaval:
                        position_symbols = [p["symbol"] for p in positions]
                        if symbol not in position_symbols:
                            quote_short = fmpsdk.get_quote_short(symbol)
                            rt_price = quote_short["price"]
                            trans_log = "* buy {} at ${} *".format(symbol, rt_price)
                            trans_line = ""
                            for i in range(0, len(trans_log)):
                                trans_line += "*"
                            print_log(ny_now, trans_line)
                            print_log(ny_now, trans_log)
                            print_log(ny_now, trans_line)
                            positions.append(
                                {
                                    "symbol": symbol,
                                    "cost": rt_price,
                                }
                            )

                    # sell signal
                    if cur_price < cur_smaval and pre_price >= pre_smaval:
                        for i in range(0, len(positions)):
                            if symbol == positions[i]["symbol"]:
                                cost_price = positions[i]["cost"]
                                quote_short = fmpsdk.get_quote_short(symbol)
                                rt_price = quote_short["price"]
                                trans_log = "* sell {} at ${}, cost ${} ({}%) *".format(
                                    symbol,
                                    rt_price,
                                    cost_price,
                                    round(
                                        (rt_price - cost_price) / cost_price * 100,
                                        2,
                                    ),
                                )
                                trans_line = ""
                                for i in range(0, len(trans_log)):
                                    trans_line += "*"
                                print_log(ny_now, trans_line)
                                print_log(ny_now, trans_log)
                                print_log(ny_now, trans_line)
                                del positions[i]
                                break
    except:
        print("[{}] transaction job failed".format(ny_now))

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

    now = datetime.now()
    # prepare log files
    logging.basicConfig(
        filename="logs/gainers-{}.txt".format(now.strftime("%Y-%m-%d")),
        level=logging.INFO,
        format="%(asctime)s, %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

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