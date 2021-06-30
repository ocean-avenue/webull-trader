# -*- coding: utf-8 -*-

# Momo day trading class, only trade in extended hour (include new high condition)

from trading.day_momo import DayTradingMomo
from sdk import webullsdk
from scripts import utils


class DayTradingMomoExtendedHour(DayTradingMomo):

    def get_tag(self):
        return "DayTradingMomoExtendedHour"

    def check_if_trade_price_new_high(self, symbol, price):
        if symbol in self.tracking_stats and self.tracking_stats[symbol]['last_trade_high'] != None:
            last_trade_high = self.tracking_stats[symbol]['last_trade_high']
            return price > last_trade_high
        return True

    def on_update(self):

        # only trading in extended hour
        if self.is_regular_market_hour():
            self.trading_end = True
            return

        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # init stats if not
            self.init_tracking_stats_if_not(ticker)
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if self.is_pre_market_hour():
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
            # check gap change
            if change_percentage >= self.min_surge_change_ratio and self.check_if_track_symbol(symbol):
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
                m2_bars = utils.convert_2m_bars(m1_bars)
                if m2_bars.empty:
                    continue
                # use latest 2 candle
                latest_candle = m2_bars.iloc[-1]
                latest_candle2 = m2_bars.iloc[-2]
                # check if trasaction amount meets requirement
                if self.check_track(latest_candle) or self.check_track(latest_candle2):
                    # found trading ticker
                    ticker = self.get_init_tracking_ticker(
                        symbol, ticker_id)
                    self.tracking_tickers[symbol] = ticker
                    utils.print_trading_log(
                        "Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
