# -*- coding: utf-8 -*-

# Momo day trade, no entry if the price not break max of last high price.

from scripts import utils
from webull_trader.enums import AlgorithmType
from trading.day_momo import DayTradingMomo


class DayTradingMomoNewHigh(DayTradingMomo):

    def print_algo_name(self):
        print("[{}] {}".format(utils.get_now(),
              AlgorithmType.tostr(AlgorithmType.DAY_MOMENTUM_NEW_HIGH)))

    def check_if_price_new_high(self, symbol, price):
        last_high_price = self.trading_stats[symbol]['last_high_price']
        return price > last_high_price


def start():
    from scripts import utils
    from trading.day_momo_newhigh import DayTradingMomoNewHigh

    paper = utils.check_paper()
    daytrading = DayTradingMomoNewHigh(paper=paper)
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()
