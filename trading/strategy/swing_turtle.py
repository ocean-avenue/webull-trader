# -*- coding: utf-8 -*-

# Turtle trading

from typing import List
from common import config, constants
from trading import pattern
from trading.strategy.strategy_base import StrategyBase
from logger import trading_logger
from common.enums import ActionType, SetupType
from webull_trader.models import ManualTradeRequest, StockQuote, SwingHistoricalDailyBar, SwingPosition, SwingWatchlist


class SwingTurtle(StrategyBase):

    from common.enums import SetupType, TradingHourType
    from webull_trader.models import ManualTradeRequest, SwingHistoricalDailyBar, SwingPosition

    def __init__(self, paper, trading_hour: TradingHourType, entry_period: int = 55, exit_period: int = 20):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.watchlist: List[dict] = []
        self.entry_period: int = entry_period
        self.exit_period: int = exit_period

    def get_tag(self) -> str:
        return "SwingTurtle"

    def get_setup(self) -> SetupType:
        if self.entry_period == 20:
            return SetupType.SWING_20_DAYS_NEW_HIGH
        return SetupType.SWING_55_DAYS_NEW_HIGH

    def get_buy_order_limit(self, unit_weight: int):
        return self.swing_position_amount_limit * unit_weight

    def check_has_volume(self, daily_bars: List[SwingHistoricalDailyBar]) -> bool:
        if not pattern.check_daily_bars_volume_grinding(daily_bars, period=4) and \
                not pattern.check_daily_bars_rel_volume(daily_bars):
            return False
        return True

    def check_period_high(self, daily_bars: List[SwingHistoricalDailyBar]) -> bool:
        latest_close = daily_bars[-1].close
        latest_sma120 = daily_bars[-1].sma_120
        period_close = daily_bars[self.entry_period].close
        ROC = (latest_close - period_close) / period_close * 100
        # make sure is uptrend and trend is strong
        if latest_close > latest_sma120 and ROC > config.SWING_PRICE_RATE_OF_CHANGE:
            # get entry_period highest
            entry_period_highest = 0
            # entry_period_highest_idx = -1
            for i in range(len(daily_bars) - self.entry_period - 1, len(daily_bars) - 1):
                daily_bar = daily_bars[i]
                if daily_bar.close > entry_period_highest:
                    entry_period_highest = daily_bar.close
                    # entry_period_highest_idx = i
            # check if entry_period new high, and period high is not in last 5 days

            # and entry_period_highest_idx < (len(daily_bars) - 6):
            if latest_close > entry_period_highest:
                return True
        return False

    def check_period_low(self, daily_bars: List[SwingHistoricalDailyBar]) -> bool:
        if len(daily_bars) <= self.exit_period:
            return False
        latest_close = daily_bars[-1].close
        # get exit_period lowest
        exit_period_lowest = constants.MAX_SECURITY_PRICE
        for i in range(len(daily_bars) - self.exit_period - 1, len(daily_bars) - 1):
            daily_bar = daily_bars[i]
            if daily_bar.close < exit_period_lowest:
                exit_period_lowest = daily_bar.close
        # check if exit_period new low
        if latest_close < exit_period_lowest:
            return True
        return False

    def check_scale_in(self, daily_bars: List[SwingHistoricalDailyBar], swing_position: SwingPosition) -> bool:
        # already full positions
        if swing_position.units >= swing_position.target_units:
            return False
        latest_close = daily_bars[-1].close
        # not meet add unit price
        if latest_close < swing_position.add_unit_price:
            return False
        # check ROC
        period_close = daily_bars[self.entry_period].close
        ROC = (latest_close - period_close) / period_close * 100
        if ROC < config.SWING_SCALE_PRICE_RATE_OF_CHANGE:
            return False
        return True

    def trade(self, watchlist: List[dict]):
        symbol = watchlist["symbol"]
        unit_weight = watchlist["unit_weight"]
        # check if already has possition
        position = SwingPosition.objects.filter(
            symbol=symbol, setup=self.get_setup()).first()
        if position:
            # get exit_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            current_daily_bars = list(hist_daily_bars)
            latest_close = current_daily_bars[-1].close
            # check period low for exit
            if self.check_period_low(current_daily_bars):
                self.submit_sell_market_order(
                    symbol, position, latest_close, reason="period low")
            elif latest_close < position.stop_loss_price:  # check if stop loss
                self.submit_sell_market_order(
                    symbol, position, latest_close, reason="stop loss")
            elif self.check_scale_in(current_daily_bars, position):  # check if add unit
                self.submit_buy_market_order(
                    symbol, position, unit_weight, latest_close, reason="add unit")
        else:
            # check if buy
            # get entry_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            current_daily_bars = list(hist_daily_bars)
            # prev_daily_bars = current_daily_bars[0:len(current_daily_bars)-1]
            if len(current_daily_bars) > self.entry_period:
                # check period high for entry
                if self.check_period_high(current_daily_bars):
                    # check daily bars has volume
                    if self.check_has_volume(current_daily_bars):
                        latest_close = current_daily_bars[-1].close
                        self.submit_buy_market_order(
                            symbol, None, unit_weight, latest_close, reason="period high")
                    else:
                        trading_logger.log(
                            "<{}> daily chart has not enough volume, no entry!".format(symbol))
            else:
                trading_logger.log(
                    "<{}> daily chart has not enough data, no entry!".format(symbol))

    def manual_trade(self, request: ManualTradeRequest):
        symbol = request.symbol
        quantity = request.quantity
        action = request.action
        if action == ActionType.BUY:
            # TODO, support manual buy order
            pass
        else:
            # check if already has possition
            position = SwingPosition.objects.filter(
                symbol=symbol, setup=self.get_setup(), quantity=quantity).first()
            if position:
                latest_price = 0.0
                quote = StockQuote.objects.filter(symbol=symbol).first()
                if quote:
                    latest_price = quote.price
                self.submit_sell_market_order(
                    symbol, position, latest_price, reason="manual request", manual_request=request)
            else:
                trading_logger.log(
                    f"Unable to find match position <{symbol}>, quant: {quantity} for sell manual request.")
        # mark request done
        request.complete = True
        request.save()

    def begin(self):
        # only trade regular market hour once
        if not self.is_regular_market_hour():
            return
        # load swing watchlist
        swing_watchlist = SwingWatchlist.objects.all()
        for watchlist in swing_watchlist:
            self.watchlist.append({
                "symbol": watchlist.symbol,
                "unit_weight": watchlist.unit_weight,
            })

    def update(self):
        # only trade regular market hour once
        if not self.is_regular_market_hour():
            return

        # manual request first
        manual_request = ManualTradeRequest.objects.filter(
            setup=self.get_setup(), complete=False).first()
        if manual_request:
            self.manual_trade(manual_request)
            return

        # swing trading one symbol in each update
        if len(self.watchlist) > 0:
            watchlist = self.watchlist[0]
            # swing trade using market order
            self.trade(watchlist)
            # remove from swing_symbols
            del self.watchlist[0]

    def end(self):
        self.trading_end = True
