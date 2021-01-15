import time
import schedule
import fmpsdk
from datetime import datetime


def day_trading_job():
    now = datetime.now()
    most_gainers = fmpsdk.get_most_gainer_stock_companies()
    if len(most_gainers) > 3:
        gainer_1 = most_gainers[0]
        gainer_2 = most_gainers[1]
        gainer_3 = most_gainers[2]
        print(
            "[{}] {} {}, {} {}, {} {}".format(
                now,
                gainer_1["ticker"],
                gainer_1["changesPercentage"],
                gainer_2["ticker"],
                gainer_2["changesPercentage"],
                gainer_3["ticker"],
                gainer_3["changesPercentage"],
            )
        )

    if now.hour == 13:
        return schedule.CancelJob


def start_trading_job():
    schedule.every(60).seconds.do(day_trading_job)


schedule.every().monday.at("06:30").do(start_trading_job)
schedule.every().tuesday.at("06:30").do(start_trading_job)
schedule.every().wednesday.at("06:30").do(start_trading_job)
schedule.every().thursday.at("06:30").do(start_trading_job)
schedule.every().friday.at("06:30").do(start_trading_job)


while True:
    schedule.run_pending()
    time.sleep(1)