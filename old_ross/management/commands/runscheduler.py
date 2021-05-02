# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from sdk import fmpsdk
from scripts import paper_trading, fetch_orders, fetch_news, fetch_histdata, utils

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


def paper_trading_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip paper trading job...".format(
            utils.get_now(), holiday))
        return
    print("[{}] start paper trading job...".format(utils.get_now()))
    paper_trading.start()
    print("[{}] done paper trading job!".format(utils.get_now()))


def fetch_stats_data_job():
    holiday = _check_market_holiday()
    if holiday != None:
        print("[{}] {}, skip fetch data job...".format(
            utils.get_now(), holiday))
        return

    print("[{}] start fetch orders job...".format(utils.get_now()))
    fetch_orders.start()
    print("[{}] done fetch orders job!".format(utils.get_now()))

    print("[{}] start fetch news job...".format(utils.get_now()))
    fetch_news.start()
    print("[{}] done fetch news job!".format(utils.get_now()))

    print("[{}] start fetch hist data job...".format(utils.get_now()))
    fetch_histdata.start()
    print("[{}] done fetch hist data job!".format(utils.get_now()))


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

        paper = utils.check_paper()

        if paper:
            # pre-market paper trading jobs
            add_weekday_jobs(
                job=paper_trading_job,
                job_name="paper_trading_job_premarket",
                hour="04",
                minute="00")

            # regular hour paper trading jobs
            add_weekday_jobs(
                job=paper_trading_job,
                job_name="paper_trading_job",
                hour="09",
                minute="30")

            # post-market paper trading jobs
            add_weekday_jobs(
                job=paper_trading_job,
                job_name="paper_trading_job_postmarket",
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
