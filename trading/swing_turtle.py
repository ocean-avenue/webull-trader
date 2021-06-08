# -*- coding: utf-8 -*-

# Turtle trading

from django.utils import timezone
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from webull_trader.models import SwingHistoricalDailyBar, SwingPosition, SwingWatchlist
from sdk import webullsdk


class SwingTurtle(StrategyBase):

    def __init__(self, paper, trading_hour, entry_period=55, exit_period=20):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.entry_period = entry_period
        self.exit_period = exit_period

    def get_tag(self):
        return "SwingTurtle"

    def get_setup(self):
        if self.entry_period == 20:
            return SetupType.SWING_20_DAYS_NEW_HIGH
        return SetupType.SWING_55_DAYS_NEW_HIGH

    def get_buy_order_limit(self, units):
        return self.swing_position_amount_limit * units

    def check_period_high(self, daily_bars):
        if len(daily_bars) <= self.entry_period:
            return False
        latest_bar = daily_bars[-1]
        latest_close = latest_bar.close
        latest_sma120 = latest_bar.sma_120
        # make sure is uptrend
        if latest_close > latest_sma120:
            # get entry_period highest
            entry_period_highest = 0
            entry_period_highest_idx = -1
            for i in range(len(daily_bars) - self.entry_period - 1, len(daily_bars) - 1):
                daily_bar = daily_bars[i]
                if daily_bar.close > entry_period_highest:
                    entry_period_highest = daily_bar.close
                    entry_period_highest_idx = i
            # check if entry_period new high, and period high is not in last 5 days
            if latest_close > entry_period_highest and entry_period_highest_idx < (len(daily_bars) - 6):
                return True
        return False

    def check_period_low(self, daily_bars):
        if len(daily_bars) <= self.exit_period:
            return False
        latest_bar = daily_bars[-1]
        latest_close = latest_bar.close
        # get exit_period lowest
        exit_period_lowest = 99999
        for i in range(len(daily_bars) - self.exit_period - 1, len(daily_bars) - 1):
            daily_bar = daily_bars[i]
            if daily_bar.close < exit_period_lowest:
                exit_period_lowest = daily_bar.close
        # check if exit_period new low
        if latest_close < exit_period_lowest:
            return True
        return False

    def trade(self, watchlist):
        symbol = watchlist["symbol"]
        units = watchlist["units"]
        # check if already has possition
        position = SwingPosition.objects.filter(
            symbol=symbol, setup=self.get_setup()).first()
        if position:
            # check if sell
            # get exit_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            current_daily_bars = list(hist_daily_bars)
            if self.check_period_low(current_daily_bars):
                latest_close = current_daily_bars[-1].close
                ticker_id = webullsdk.get_ticker(symbol)
                # submit market sell order
                order_response = webullsdk.sell_market_order(
                    ticker_id=ticker_id,
                    quant=position.quantity)
                self.print_log("🔴 Submit sell order <{}>[{}], quant: {}, latest price: {}".format(
                    symbol, ticker_id, position.quantity, latest_close))
                # add swing trade
                self.add_swing_trade(
                    symbol=symbol,
                    order_response=order_response,
                    position=position,
                    price=latest_close,
                    sell_time=timezone.now())
                # clear position
                position.delete()
        else:
            # check if buy
            # get entry_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            current_daily_bars = list(hist_daily_bars)
            # prev_daily_bars = current_daily_bars[0:len(current_daily_bars)-1]

            # first period high
            if self.check_period_high(current_daily_bars):
                latest_close = current_daily_bars[-1].close
                # buy swing position amount
                buy_position_amount = self.get_buy_order_limit(units)
                buy_quant = (int)(buy_position_amount / latest_close)
                # make sure usable cash is enough
                portfolio = webullsdk.get_portfolio()
                usable_cash = float(portfolio['usableCash'])
                if buy_quant > 0 and usable_cash > self.day_trade_usable_cash_threshold:
                    ticker_id = webullsdk.get_ticker(symbol)
                    # submit market buy order
                    order_response = webullsdk.buy_market_order(
                        ticker_id=ticker_id,
                        quant=buy_quant)
                    self.print_log("🟢 Submit buy order <{}>[{}], quant: {}, latest price: {}".format(
                        symbol, ticker_id, buy_quant, latest_close))
                    # add swing position

                    self.add_swing_position(
                        symbol,
                        order_response,
                        cost=latest_close,
                        quant=buy_quant,
                        buy_time=timezone.now(),
                        setup=self.get_setup())

    def on_begin(self):

        if not self.is_regular_market_hour():
            return

        swing_watchlist = SwingWatchlist.objects.all()
        for swing_watch in swing_watchlist:
            self.trading_watchlist.append({
                "symbol": swing_watch.symbol,
                "units": swing_watch.units,
            })

    def on_update(self):
        # only trade regular market hour once
        if not self.is_regular_market_hour():
            self.trading_end = False
            return

        # swing trading one symbol in each update
        if len(self.trading_watchlist) > 0:
            watchlist = self.trading_watchlist[0]
            # swing trade using market order
            self.trade(watchlist)
            # remove from swing_symbols
            del self.trading_watchlist[0]

        # check if trading is end
        if len(self.trading_watchlist) == 0:
            self.trading_end = True
