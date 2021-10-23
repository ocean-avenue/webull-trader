# -*- coding: utf-8 -*-

# Grinding day trading strategy with large cap and major news

from datetime import datetime, date
from trading.strategy.day_breakout import DayTradingBreakout
from common.enums import SetupType
from common import utils, config
from sdk import webullsdk, finvizsdk


class DayTradingGrindingLargeCap(DayTradingBreakout):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.large_cap_with_major_news = []

    def get_tag(self):
        return "DayTradingGrindingLargeCap"

    def get_setup(self):
        return SetupType.DAY_GRINDING_UP

    def update(self):
        # only trade in regular hour
        if not self.is_regular_market_hour():
            return

        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = webullsdk.get_top_gainers(count=50)
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = gainer["ticker_id"]
            market_value = gainer["market_value"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            # skip ticker is not large cap
            if market_value < config.LARGE_CAP_MARKET_CAP:
                continue
            # check if has news
            if symbol not in self.large_cap_with_major_news:
                quote = finvizsdk.get_quote(symbol)
                news_list = quote["news"]
                # check if has news today
                has_news_today = False
                for news in news_list:
                    news_time = news["news_time"]
                    news_datetime = datetime.strptime(
                        news_time, "%Y-%m-%d %H:%M:%S")
                    if news_datetime.date() == date.today():
                        has_news_today = True
                        title = news["title"]
                        source = news["source"]
                        news_link = news["news_link"]
                        utils.print_trading_log(
                            "Found <{}> news!".format(symbol))
                        utils.print_trading_log("Title: {}".format(title))
                        utils.print_trading_log("Source: {}".format(source))
                        utils.print_trading_log("Time: {}".format(news_time))
                        utils.print_trading_log("Link: {}".format(news_link))
                if not has_news_today:
                    continue
                # find news today
                self.large_cap_with_major_news.append(symbol)
            # trade if is large cap with news
            if symbol in self.large_cap_with_major_news:
                ticker = self.build_tracking_ticker(symbol, ticker_id)
                # found trading ticker
                self.tracking_tickers[symbol] = ticker
                utils.print_trading_log("Found <{}> to trade!".format(symbol))
                # do trade
                self.trade(ticker)


# Grinding day trading strategy with specific symbols

class DayTradingGrindingSymbols(DayTradingBreakout):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.trading_tickers = []

    def get_tag(self):
        return "DayTradingGrindingSymbols"

    def get_setup(self):
        return SetupType.DAY_GRINDING_UP

    def begin(self):
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

    def update(self):
        # only trade in pre-market and regular hour
        if self.is_after_market_hour():
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
