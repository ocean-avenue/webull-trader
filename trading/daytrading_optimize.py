# -*- coding: utf-8 -*-

# Day Trading
# Dynamic Optimize - Trade based on win rate, reduce size if win rate is low.


from scripts import utils
from datetime import datetime, timedelta
from trading.daytrading_base import DayTradingBase


class DayTradingOptimize(DayTradingBase):

    def call_before(self):
        print("[{}] Dynamic Optimize - Trade based on win rate, reduce size if win rate is low.".format(utils.get_now()))

    def get_buy_order_limit(self, symbol):
        buy_position_amount = self.order_amount_limit
        # check win rate
        if symbol in self.trading_stats:
            win_rate = float(
                self.trading_stats[symbol]['win_trades']) / self.trading_stats[symbol]['trades']
            buy_position_amount = max(
                self.order_amount_limit * win_rate, self.order_amount_limit * 0.3)
        return buy_position_amount

    def check_continue_3loss(self, symbol):
        if symbol in self.trading_stats and self.trading_stats[symbol]['continue_lose_trades'] >= 3 and (datetime.now() - self.trading_stats[symbol]['last_trade_time']) <= timedelta(seconds=self.blacklist_timeout_in_sec):
            return True
        return False


def start():
    from scripts import utils
    from trading.daytrading_optimize import DayTradingOptimize

    paper = utils.check_paper()
    daytrading = DayTradingOptimize(paper=paper)
    if paper:
        print("[{}] Start PAPER day trading...".format(utils.get_now()))
    else:
        print("[{}] Start LIVE day trading...".format(utils.get_now()))
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()
