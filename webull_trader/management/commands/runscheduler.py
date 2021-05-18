# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from sdk import fmpsdk
from scripts import fetch_account, fetch_orders, fetch_news, fetch_histdata, calculate_histdata, utils
from trading import day_momo, day_momo_reduce
from webull_trader.enums import AlgorithmType

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]

scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
scheduler.add_jobstore(DjangoJobStore(), "default")


def _check_market_holiday():
    today = datetime.today()
    if today.weekday() >= 5:
        return "Weekend"
    market_hour = fmpsdk.get_market_hour()
    market_holidays = market_hour['stockMarketHolidays']
    today_str = today.strftime("%Y-%m-%d")
    year = today.year
    holiday = None
    for market_holiday in market_holidays:
        if market_holiday['year'] == year:
            for key, val in market_holiday.items():
                if val == today_str:
                    holiday = key
                    break
    return holiday


def day_trading_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip day trading job...".format(
            utils.get_now(), holiday))
        return
    print("[{}] Start day trading job...".format(utils.get_now()))
    # load algo type
    algo_type = utils.get_algo_type()
    if algo_type == AlgorithmType.DAY_MOMENTUM:
        # momo trade
        day_momo.start()
    elif algo_type == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
        # momo trade with reduce size
        day_momo_reduce.start()
    else:
        print("[{}] No day trading job found, skip...".format(utils.get_now()))
    print("[{}] Done day trading job!".format(utils.get_now()))


def swing_trading_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip swing trading job...".format(
            utils.get_now(), holiday))
        return
    print("[{}] Start swing trading job...".format(utils.get_now()))
    # load algo type
    algo_type = utils.get_algo_type()
    if algo_type == AlgorithmType.SWING_TURTLE:
        # turtle trading
        # TODO
        pass
    else:
        print("[{}] No swing trading job found, skip...".format(utils.get_now()))
    print("[{}] Done swing trading job!".format(utils.get_now()))


def fetch_stats_data_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip fetch data job...".format(
            utils.get_now(), holiday))
        return

    print("[{}] Start fetch account job...".format(utils.get_now()))
    fetch_account.start()
    print("[{}] Done fetch account job!".format(utils.get_now()))

    print("[{}] Start fetch orders job...".format(utils.get_now()))
    fetch_orders.start()
    print("[{}] Done fetch orders job!".format(utils.get_now()))

    print("[{}] Start fetch news job...".format(utils.get_now()))
    fetch_news.start()
    print("[{}] Done fetch news job!".format(utils.get_now()))

    print("[{}] Start fetch hist data job...".format(utils.get_now()))
    fetch_histdata.start()
    print("[{}] Done fetch hist data job!".format(utils.get_now()))

    print("[{}] Start calculate hist data job...".format(utils.get_now()))
    calculate_histdata.start()
    print("[{}] Done calculate hist data job!".format(utils.get_now()))


def add_weekday_jobs(job, job_name, hour, minute, second="00"):
    for weekday in WEEKDAYS:
        scheduler.add_job(
            job,
            trigger=CronTrigger(
                day_of_week=weekday, hour=hour, minute=minute, second=second
            ),
            id="{}_{}".format(job_name, weekday),
            max_instances=1,
            replace_existing=True,
        )


class Command(BaseCommand):
    help = "runs apscheduler"

    def handle(self, *args, **options):

        # pre-market day trading jobs
        add_weekday_jobs(
            job=day_trading_job,
            job_name="day_trading_job_bmo",
            hour="04",
            minute="00")

        # regular hour day trading jobs
        add_weekday_jobs(
            job=day_trading_job,
            job_name="day_trading_job",
            hour="09",
            minute="30")

        # post-market day trading jobs
        add_weekday_jobs(
            job=day_trading_job,
            job_name="day_trading_job_amc",
            hour="16",
            minute="00")

        # fetch stats data after trading
        add_weekday_jobs(
            job=fetch_stats_data_job,
            job_name="fetch_stats_data_job",
            hour="20",
            minute="15")

        try:
            print("[{}] start scheduler...".format(utils.get_now()))
            scheduler.start()
        except KeyboardInterrupt:
            print("[{}] stopping scheduler...".format(utils.get_now()))
            scheduler.shutdown()
            print("[{}] scheduler shut down successfully!".format(utils.get_now()))
