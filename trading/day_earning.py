# -*- coding: utf-8 -*-

# Earning day trading class

import time
from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


class DayTradingEarning(StrategyBase):

    def get_tag(self):
        return "DayTradingEarning"

    def get_setup(self):
        return SetupType.DAY_EARNING_GAP

    def check_entry(self, ticker, bars):
        return False

    def check_stop_loss(self, ticker, position):
        return (False, None)

    def check_exit(self, ticker, bars):
        return (False, None)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

    def on_begin(self):
        # get earning calendar
        pass

    def on_update(self):
        # trading tickers
        pass

    def on_end(self):
        self.trading_end = True

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.get_trading_hour(), date.today())
