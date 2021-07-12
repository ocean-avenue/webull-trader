# -*- coding: utf-8 -*-

# Grinding day trading strategy with specific symbols

from trading.day_breakout import DayTradingBreakout
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


class DayTradingGrindingSymbols(DayTradingBreakout):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.trading_tickers = []

    def get_tag(self):
        return "DayTradingGrindingSymbols"

    def get_setup(self):
        return SetupType.DAY_GRINDING_UP

    def on_begin(self):
        # only trade in pre-market and regular hour
        if self.is_after_market_hour():
            return

        # trading specific symbols
        trading_symbols = utils.get_trading_symbols()
        for symbol in trading_symbols:
            ticker_id = webullsdk.get_ticker(symbol=symbol)
            self.trading_tickers.append({
                "symbol": symbol,
                "ticker_id": ticker_id,
            })
            utils.print_trading_log(
                "Tracking <{}> for grinding up...".format(symbol))

    def on_update(self):
        # only trade in pre-market and regular hour
        if not self.is_after_market_hour():
            return

        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        for trading_ticker in self.trading_tickers:
            symbol = trading_ticker["symbol"]
            ticker_id = trading_ticker["ticker_id"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            # found trading ticker
            self.tracking_tickers[symbol] = ticker
            utils.print_trading_log("Found <{}> to trade!".format(symbol))
            # do trade
            self.trade(ticker)
