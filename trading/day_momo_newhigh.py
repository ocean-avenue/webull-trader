# -*- coding: utf-8 -*-

# Momo day trade, no entry if the price not break max of last high price.

from trading.day_momo import DayTradingMomo


class DayTradingMomoNewHigh(DayTradingMomo):

    def get_tag(self):
        return "DayTradingMomoNewHigh"

    def check_if_trade_price_new_high(self, ticker, price):
        symbol = ticker['symbol']
        if symbol in self.tracking_stats and self.tracking_stats[symbol]['last_trade_high'] != None:
            last_trade_high = self.tracking_stats[symbol]['last_trade_high']
            return price > last_trade_high
        return True
