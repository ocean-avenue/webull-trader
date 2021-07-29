# -*- coding: utf-8 -*-

# Breakout day trade, exit if trading period timeout.

from datetime import datetime, timedelta
from scripts import config
from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutPeriod(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutPeriod"

    def check_if_trade_period_timeout(self, ticker):
        if (datetime.now() - ticker['last_buy_time']) >= timedelta(seconds=config.DAY_PERIOD_TIMEOUT_IN_SEC):
            return True
        return False
