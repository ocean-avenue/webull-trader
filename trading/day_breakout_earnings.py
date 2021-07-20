# -*- coding: utf-8 -*-

# Breakout day trading class, will check earning stock during earning date

from datetime import date

from trading.day_breakout import DayTradingBreakout
from webull_trader.enums import SetupType
from webull_trader.models import EarningCalendar
from sdk import webullsdk
from scripts import utils, config


class DayTradingBreakoutEarnings(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutEarnings"

    def get_setup(self):
        if len(self.earning_tickers) == 0:
            if self.entry_period == 30:
                return SetupType.DAY_30_CANDLES_NEW_HIGH
            elif self.entry_period == 20:
                return SetupType.DAY_20_CANDLES_NEW_HIGH
            return SetupType.DAY_10_CANDLES_NEW_HIGH
        else:
            return SetupType.DAY_EARNINGS_GAP

    def check_trade(self, symbol, ticker_id, change_percentage):
        ticker = self.build_tracking_ticker(symbol, ticker_id)
        # check if can trade with requirements
        if not self.check_can_trade_ticker(ticker):
            return
        # check gap change
        if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
            if self.is_extended_market_hour():
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.entry_period+5))
                if m1_bars.empty:
                    return
                # use latest 2 candle
                latest_candle = m1_bars.iloc[-1]
                latest_candle2 = m1_bars.iloc[-2]
                # check if trasaction amount and volume meets requirement
                if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                    # found trading ticker
                    self.tracking_tickers[symbol] = ticker
                    utils.print_trading_log(
                        "Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
            elif self.is_regular_market_hour():
                # found trading ticker
                self.tracking_tickers[symbol] = ticker
                utils.print_trading_log("Found <{}> to trade!".format(symbol))
                # do trade
                self.trade(ticker)

    def on_begin(self):
        self.earning_tickers = []
        # check earning calendars
        today = date.today()
        if self.is_pre_market_hour() or self.is_regular_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="bmo")
        elif self.is_after_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="amc")
        # update earning_tickers
        for earning in earnings:
            symbol = earning.symbol
            ticker_id = webullsdk.get_ticker(symbol=symbol)
            self.earning_tickers.append({
                "symbol": symbol,
                "ticker_id": ticker_id,
            })
            utils.print_trading_log(
                "Add ticker <{}> to check earning gap!".format(symbol))

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        # no earning symbol found
        if len(self.earning_tickers) == 0:
            # find trading ticker in top gainers
            top_gainers = []
            if self.is_regular_market_hour():
                top_gainers = webullsdk.get_top_gainers()
            elif self.is_pre_market_hour():
                top_gainers = webullsdk.get_pre_market_gainers()
            elif self.is_after_market_hour():
                top_gainers = webullsdk.get_after_market_gainers()

            # utils.print_trading_log("Scanning top gainers <{}>...".format(
            #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
            for gainer in top_gainers:
                symbol = gainer["symbol"]
                # check if ticker already in monitor
                if symbol in self.tracking_tickers:
                    continue
                ticker_id = gainer["ticker_id"]
                # utils.print_trading_log("Scanning <{}>...".format(symbol))
                change_percentage = gainer["change_percentage"]
                self.check_trade(symbol, ticker_id, change_percentage)
        else:
            for earning_ticker in self.earning_tickers:
                symbol = earning_ticker["symbol"]
                ticker_id = earning_ticker["ticker_id"]
                # check if ticker already in monitor
                if symbol in self.tracking_tickers:
                    continue
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    continue
                change_percentage = 0.0
                if self.is_extended_market_hour():
                    if 'pChRatio' in quote:
                        change_percentage = float(quote['pChRatio'])
                elif self.is_regular_market_hour():
                    if 'changeRatio' in quote:
                        change_percentage = float(quote['changeRatio'])
                self.check_trade(symbol, ticker_id, change_percentage)
