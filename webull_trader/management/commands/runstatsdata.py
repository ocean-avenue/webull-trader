from datetime import datetime
from django.core.management.base import BaseCommand
from scripts import utils, fetch_account, fetch_orders, fetch_news, fetch_earnings, fetch_histdata, calculate_histdata, adjust_trades


class Command(BaseCommand):
    help = 'run fetch stats data'

    def add_arguments(self, parser):
        parser.add_argument('date', type=str)

    def handle(self, *args, **options):
        date = datetime.strptime(options['date'], '%Y-%m-%d').date()
        print("[{}] Start fetch account job...".format(utils.get_now()))
        fetch_account.start(day=date)
        print("[{}] Done fetch account job!".format(utils.get_now()))

        print("[{}] Start fetch orders job...".format(utils.get_now()))
        fetch_orders.start()
        print("[{}] Done fetch orders job!".format(utils.get_now()))

        print("[{}] Start adjust trades job...".format(utils.get_now()))
        adjust_trades.start()
        print("[{}] Done adjust trades job!".format(utils.get_now()))

        print("[{}] Start fetch news job...".format(utils.get_now()))
        fetch_news.start(day=date)
        print("[{}] Done fetch news job!".format(utils.get_now()))

        print("[{}] Start fetch earnings job...".format(utils.get_now()))
        fetch_earnings.start()
        print("[{}] Done fetch earnings job!".format(utils.get_now()))

        print("[{}] Start fetch hist data job...".format(utils.get_now()))
        fetch_histdata.start(day=date)
        print("[{}] Done fetch hist data job!".format(utils.get_now()))

        print("[{}] Start calculate hist data job...".format(utils.get_now()))
        calculate_histdata.start(day=date)
        print("[{}] Done calculate hist data job!".format(utils.get_now()))
