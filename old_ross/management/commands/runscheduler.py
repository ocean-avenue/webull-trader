# -*- coding: utf-8 -*-
from datetime import datetime
from django.conf import settings
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from django.core.management.base import BaseCommand
from django_apscheduler.jobstores import DjangoJobStore
from sdk import fmpsdk
from scripts import paper_trading, utils

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

        try:
            print("[{}] start scheduler...".format(utils.get_now()))
            scheduler.start()
        except KeyboardInterrupt:
            print("[{}] stopping scheduler...".format(utils.get_now()))
            scheduler.shutdown()
            print("[{}] scheduler shut down successfully!".format(utils.get_now()))
