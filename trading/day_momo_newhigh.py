# -*- coding: utf-8 -*-

# Momo day trade, no entry if the price not break max of last high price.

from trading.day_momo import DayTradingMomo


class DayTradingMomoNewHigh(DayTradingMomo):

    def get_tag(self):
        return "DayTradingMomoNewHigh"

    def check_if_price_new_high(self, symbol, price):
        if symbol in self.trading_stats:
            last_high_price = self.trading_stats[symbol]['last_high_price']
            return price > last_high_price
        return True
