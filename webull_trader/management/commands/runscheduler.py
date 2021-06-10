# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from sdk import fmpsdk
from scripts import fetch_account, fetch_quotes, fetch_orders, fetch_news, fetch_earnings, fetch_histdata, calculate_histdata, utils
from trading import trading_executor

WEEKDAYS = ["mon", "tue", "wed", "thu", "fri"]
REGULAR_HOURS = ["10", "11", "12", "13", "14", "15", "16"]

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


def trading_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip trading job...".format(
            utils.get_now(), holiday))
        return
    print("[{}] Start trading job...".format(utils.get_now()))
    trading_executor.start()
    print("[{}] Done trading job!".format(utils.get_now()))


def fetch_stock_quote_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip fetch stock quote job...".format(
            utils.get_now(), holiday))
        return

    print("[{}] Start fetch quotes job...".format(utils.get_now()))
    fetch_quotes.start()
    print("[{}] Done fetch quotes job!".format(utils.get_now()))


def fetch_stats_data_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip fetch stats data job...".format(
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

    print("[{}] Start fetch earnings job...".format(utils.get_now()))
    fetch_earnings.start()
    print("[{}] Done fetch earnings job!".format(utils.get_now()))

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


def add_regular_hour_jobs(job, job_name):
    for weekday in WEEKDAYS:
        for regular_hour in REGULAR_HOURS:
            scheduler.add_job(
                job,
                trigger=CronTrigger(
                    day_of_week=weekday, hour=regular_hour, minute="00", second="00"
                ),
                id="{}_{}_{}".format(job_name, weekday, regular_hour),
                max_instances=1,
                replace_existing=True,
            )


class Command(BaseCommand):
    help = "runs apscheduler"

    def handle(self, *args, **options):

        # pre-market trading jobs
        add_weekday_jobs(
            job=trading_job,
            job_name="trading_job_bmo",
            hour="04",
            minute="00")

        # regular hour trading jobs
        add_weekday_jobs(
            job=trading_job,
            job_name="trading_job",
            hour="09",
            minute="30")

        # post-market trading jobs
        add_weekday_jobs(
            job=trading_job,
            job_name="trading_job_amc",
            hour="16",
            minute="00")

        # fetch stats data after trading
        add_weekday_jobs(
            job=fetch_stats_data_job,
            job_name="fetch_stats_data_job",
            hour="20",
            minute="15")

        # fetch stock quote
        add_regular_hour_jobs(
            job=fetch_stock_quote_job,
            job_name="fetch_stock_quote_job",
        )

        try:
            print("[{}] start scheduler...".format(utils.get_now()))
            scheduler.start()
        except KeyboardInterrupt:
            print("[{}] stopping scheduler...".format(utils.get_now()))
            scheduler.shutdown()
            print("[{}] scheduler shut down successfully!".format(utils.get_now()))
