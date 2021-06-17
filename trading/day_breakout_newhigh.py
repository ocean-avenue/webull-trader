# -*- coding: utf-8 -*-

# Breakout day trade, no entry if the price not break max of last high price.

from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutNewHigh(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutNewHigh"

    def check_if_trade_price_new_high(self, symbol, price):
        if symbol in self.tracking_stats and self.tracking_stats[symbol]['last_trade_high'] != None:
            last_trade_high = self.tracking_stats[symbol]['last_trade_high']
            return price > last_trade_high
        return True
