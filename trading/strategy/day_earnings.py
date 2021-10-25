# -*- coding: utf-8 -*-

from datetime import date, datetime
from trading.tracker.trading_tracker import TrackingTicker
from trading.strategy.strategy_base import StrategyBase
from webull_trader.models import EarningCalendar, DayPosition
from common.enums import SetupType
from common import config
from sdk import webullsdk
from logger import trading_logger


# Earning day trading class, may holding positions overnight

class DayTradingEarningsOvernight(StrategyBase):

    from typing import Optional, Tuple
    from trading.tracker.trading_tracker import TrackingTicker
    from common.enums import SetupType

    def get_tag(self) -> str:
        return "DayTradingEarningsOvernight"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_EARNINGS_GAP

    def check_entry(self, ticker: TrackingTicker, quote: dict) -> bool:
        if 'pChRatio' in quote and float(quote['pChRatio']) >= config.MIN_EARNING_GAP_RATIO:
            return True
        return False

    def check_stop_loss(self, ticker: TrackingTicker) -> Tuple[bool, Optional[str]]:
        return (False, None)

    def check_exit(self, ticker: TrackingTicker) -> Tuple[bool, Optional[str]]:
        if datetime.now().hour > 12:
            return (True, "Sell at 12:00 PM.")
        return (False, None)

    def trade(self, ticker: TrackingTicker):
        ticker_id = ticker.get_id()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)
            return

        # buy in pre/after market hour
        if self.is_extended_market_hour():
            quote = webullsdk.get_quote(ticker_id=ticker_id)
            if quote == None:
                return
            if self.check_entry(ticker, quote):
                # submit buy limit order
                self.submit_buy_limit_order(ticker)

        # sell in regular market hour
        if self.is_regular_market_hour():
            exit_trading, exit_note = self.check_exit(ticker)
            if exit_trading:
                # submit sell limit order
                self.submit_sell_limit_order(
                    ticker, note=exit_note, retry=True, retry_limit=50)

    def begin(self):
        # prepare tickers for buy
        if self.is_extended_market_hour():
            today = date.today()
            earning_time = None
            # get earning calendars
            if self.is_pre_market_hour():
                earning_time = "bmo"
            elif self.is_after_market_hour():
                earning_time = "amc"
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time=earning_time)
            # update tracking tickers
            for earning in earnings:
                symbol = earning.symbol
                ticker_id = str(webullsdk.get_ticker(symbol=symbol))
                ticker = TrackingTicker(symbol, ticker_id)
                self.trading_tracker.start_tracking(ticker)
                trading_logger.log(
                    "Add ticker <{}> to check earning gap!".format(symbol))
        # prepare tickers for sell
        if self.is_regular_market_hour():
            earning_positions = DayPosition.objects.filter(
                setup=self.get_setup())
            for position in earning_positions:
                position: DayPosition = position
                symbol = position.symbol
                ticker_id = position.ticker_id
                ticker = TrackingTicker(symbol, ticker_id)
                ticker.set_positions(position.quantity)
                ticker.set_position_obj(position)
                trading_logger.log(
                    "Add ticker <{}> to sell during regular hour!".format(symbol))
                self.trading_tracker.start_tracking(ticker)

    def update(self):
        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

    def end(self):
        self.trading_end = True
