import time
import schedule
from datetime import datetime


def day_trading_job():
    now = datetime.now()
    print("[{}] Do day trading".format(now))

    if now.hour == 13:
        return schedule.CancelJob


def start_trading_job():
    schedule.every(10).seconds.do(day_trading_job)


schedule.every().monday.at("06:30").do(start_trading_job)
schedule.every().tuesday.at("06:30").do(start_trading_job)
schedule.every().wednesday.at("06:30").do(start_trading_job)
schedule.every().thursday.at("06:30").do(start_trading_job)
schedule.every().friday.at("06:30").do(start_trading_job)


while True:
    schedule.run_pending()
    time.sleep(1)