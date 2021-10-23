# -*- coding: utf-8 -*-

from typing import List
from trading.strategy.strategy_base import StrategyBase
from common import utils
from common.enums import SetupType
from trading.tracker.trading_tracker import TrackingTicker
from webull_trader.models import DayPosition


# Clean day trading class
# this only for clean failed to sell position during last trading hour session

class DayTradingClean(StrategyBase):

    def get_tag(self) -> str:
        return "DayTradingClean"

    def get_setup(self) -> SetupType:
        return SetupType.ERROR_FAILED_TO_SELL

    def begin(self):
        # check unsold tickers
        failed_to_sell_positions: List[DayPosition] = list(DayPosition.objects.filter(
            setup=SetupType.ERROR_FAILED_TO_SELL))
        for position in failed_to_sell_positions:
            ticker = TrackingTicker(position.symbol, position.ticker_id)
            # verify has position
            ticker_position = self.get_position(ticker)
            if ticker_position == None:
                position.delete()
                continue
            ticker.set_positions(int(ticker_position['position']))
            ticker.set_position_obj(position)
            # start tracking ticker
            self.trading_tracker.start_tracking(ticker)

    def clean(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()

        if ticker.is_pending_sell():
            self.check_sell_order_done(ticker)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

        utils.print_trading_log(f"❌ Clean failed to sell position <{symbol}>!")
        self.submit_sell_limit_order(
            ticker, note="Clear failed to sell position.", retry=True, retry_limit=50)

    def update(self):
        if len(self.trading_tracker.get_tickers()) == 0:
            self.trading_end = True
            return

        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
            # clean ticker
            self.clean(ticker)
