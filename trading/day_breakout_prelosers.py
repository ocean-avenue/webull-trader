# -*- coding: utf-8 -*-

# Breakout day trade, find pre-market losers and aim for reversal.

from sdk import webullsdk
from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutPreLosers(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutPreLosers"

    def on_begin(self):
        self.preloser_tickers = []
        # check pre-market losers
        if self.is_regular_market_hour():
            self.preloser_tickers = webullsdk.get_pre_market_losers(count=10)
            self.print_log("Add {} tickers to check loser reversal!".format(
                len(self.preloser_tickers)))

    def on_update(self):

        if self.is_pre_market_hour() or self.is_after_market_hour():
            # only trade in regular hour
            return

        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # init stats if not
            self.init_tracking_stats_if_not(ticker)
            # do trade
            self.trade(ticker)

        for preloser_ticker in self.preloser_tickers:
            symbol = preloser_ticker["symbol"]
            ticker_id = preloser_ticker["ticker_id"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            # found trading ticker
            ticker = self.get_init_tracking_ticker(symbol, ticker_id)
            self.tracking_tickers[symbol] = ticker
            self.print_log("Found <{}> to trade!".format(symbol))
            # do trade
            self.trade(ticker)
