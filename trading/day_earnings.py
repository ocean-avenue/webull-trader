# -*- coding: utf-8 -*-

# Earning day trading class

import time
from datetime import date
from webull_trader.models import EarningCalendar
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


class DayTradingEarnings(StrategyBase):

    def get_tag(self):
        return "DayTradingEarnings"

    def get_setup(self):
        return SetupType.DAY_EARNINGS_GAP

    def check_entry(self, ticker, bars):
        return False

    def check_stop_loss(self, ticker, position):
        return (False, None)

    def check_exit(self, ticker, bars):
        return (False, None)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        # TODO, buy in pre/post market hour
        if utils.is_extended_market_hour():
            pass
        # TODO, sell in regular market hour
        if utils.is_regular_market_hour():
            pass

    def on_begin(self):
        today = date.today()
        earning_time = None
        # get earning calendars
        if utils.is_pre_market_hour():
            earning_time = "bmo"
        elif utils.is_after_market_hour():
            earning_time = "amc"
        earnings = EarningCalendar.objects.filter(
            earning_date=today).filter(earning_time=earning_time)
        # update tracking_tickers
        for earning in earnings:
            symbol = earning.symbol
            ticker_id = webullsdk.get_ticker(symbol=symbol)
            ticker = self.get_init_tracking_ticker(symbol, ticker_id)
            self.tracking_tickers[symbol] = ticker
            self.print_log("Add ticker <{}>[{}] to check earning gap!".format(
                symbol, ticker_id))

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # init stats if not
            self.init_tracking_stats_if_not(ticker)
            # do trade
            self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.get_trading_hour(), date.today())
