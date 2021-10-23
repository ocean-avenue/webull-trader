# -*- coding: utf-8 -*-

# Grinding day trading strategy with large cap and major news

from typing import List
from datetime import datetime, date
from trading.strategy.day_breakout import DayTradingBreakout
from common.enums import SetupType, TradingHourType
from common import utils, constants, db
from sdk import webullsdk, finvizsdk
from trading.tracker.trading_tracker import TrackingTicker


class DayTradingGrindingLargeCap(DayTradingBreakout):

    def __init__(self, paper: bool, trading_hour: TradingHourType):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.large_cap_with_major_news: List[dict] = []

    def get_tag(self) -> str:
        return "DayTradingGrindingLargeCap"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_GRINDING_UP

    def update(self):
        # only trade in regular hour
        if not self.is_regular_market_hour():
            return

        # trading tickers
        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = webullsdk.get_top_gainers(count=50)
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = str(gainer["ticker_id"])
            market_value = gainer["market_value"]
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            # skip ticker is not large cap
            if market_value < constants.LARGE_CAP_MARKET_CAP:
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
                            "Found <{}> news...".format(symbol))
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
                ticker = TrackingTicker(symbol, ticker_id)
                # found trading ticker
                self.trading_tracker.start_tracking(ticker)
                utils.print_trading_log("Start trading <{}>...".format(symbol))
                # do trade
                self.trade(ticker)


# Grinding day trading strategy with specific symbols

class DayTradingGrindingSymbols(DayTradingBreakout):

    def __init__(self, paper: bool, trading_hour: TradingHourType):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.trading_tickers: List[dict] = []

    def get_tag(self) -> str:
        return "DayTradingGrindingSymbols"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_GRINDING_UP

    def begin(self):
        # only trade in pre-market and regular hour
        if self.is_after_market_hour():
            return

        # trading specific symbols
        trading_symbols = db.get_trading_symbols()
        for symbol in trading_symbols:
            ticker_id = str(webullsdk.get_ticker(symbol=symbol))
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
        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
            # do trade
            self.trade(ticker)

        for trading_ticker in self.trading_tickers:
            symbol = trading_ticker["symbol"]
            ticker_id = trading_ticker["ticker_id"]
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            ticker = TrackingTicker(symbol, ticker_id)
            # found trading ticker
            self.trading_tracker.start_tracking(ticker)
            utils.print_trading_log("Start trading <{}>...".format(symbol))
            # do trade
            self.trade(ticker)
