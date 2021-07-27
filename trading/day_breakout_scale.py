# -*- coding: utf-8 -*-

# Breakout day trading class, scale if reach add unit price

from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutScale(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutScale"
