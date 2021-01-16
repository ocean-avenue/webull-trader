import time
import schedule
import yfsdk
# import fmpsdk
from datetime import datetime


def day_trading_job():
    now = datetime.now()
    most_gainers = yfsdk.get_most_gainers()
    if len(most_gainers) > 3:
        gainer_1 = most_gainers[0]
        gainer_2 = most_gainers[1]
        gainer_3 = most_gainers[2]
        print(
            "[{}] {} ({}, {}), {} ({}, {}), {} ({}, {})".format(
                now,
                gainer_1["symbol"],
                gainer_1["change_percentage"],
                gainer_1["market_cap"],
                gainer_2["symbol"],
                gainer_2["change_percentage"],
                gainer_2["market_cap"],
                gainer_3["symbol"],
                gainer_3["change_percentage"],
                gainer_3["market_cap"],
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
schedule.every().friday.at("20:53").do(start_trading_job)


while True:
    schedule.run_pending()
    time.sleep(1)