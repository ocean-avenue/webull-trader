from django.core.management.base import BaseCommand
from webull_trader.models import DayTrade
from scripts import calculate_histdata, adjust_trades
from common import utils


class Command(BaseCommand):
    help = 'run amend trades'

    def handle(self, *args, **options):

        # track amend dates for recalculate P&L
        amend_dates = []
        day_trades = DayTrade.objects.filter(require_adjustment=True)
        for day_trade in day_trades:
            amend_dates.append(day_trade.sell_date)

        print("[{}] Start adjust trades job...".format(utils.get_now()))
        adjust_trades.start()
        print("[{}] Done adjust trades job!".format(utils.get_now()))

        for amend_date in amend_dates:
            print("[{}] Start recalculate hist data job for {}...".format(
                utils.get_now(), amend_date))
            calculate_histdata.start(day=amend_date)
            print("[{}] Done recalculate hist data job!".format(utils.get_now()))
