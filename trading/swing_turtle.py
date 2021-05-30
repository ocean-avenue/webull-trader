# -*- coding: utf-8 -*-

# Turtle trading

from datetime import datetime
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from webull_trader.models import SwingHistoricalDailyBar, SwingPosition, SwingWatchlist
from sdk import webullsdk
from scripts import utils


class SwingTurtle(StrategyBase):

    def __init__(self, paper, entry_period=55, exit_period=20):
        super().__init__(paper=paper)
        self.entry_period = entry_period
        self.exit_period = exit_period

    def get_tag(self):
        return "SwingTurtle"

    def get_setup(self):
        if self.entry_period == 20:
            return SetupType.SWING_20_DAYS_NEW_HIGH
        return SetupType.SWING_55_DAYS_NEW_HIGH

    def get_buy_order_limit(self, symbol):
        return self.swing_position_amount_limit

    def trade(self, symbol):
        # check if already has possition
        position = SwingPosition.objects.filter(symbol=symbol)
        if position:
            # check if sell
            # get exit_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            latest_bar = hist_daily_bars.last()
            latest_close = latest_bar.close
            # get exit_period lowest
            exit_period_lowest = 99999
            for i in range(len(hist_daily_bars) - self.exit_period - 1, len(hist_daily_bars) - 1):
                daily_bar = hist_daily_bars[i]
                if daily_bar.close < exit_period_lowest:
                    exit_period_lowest = daily_bar.close
            # check if exit_period new low
            if latest_close < exit_period_lowest:
                ticker_id = webullsdk.get_ticker(symbol)
                # submit market sell order
                order_response = webullsdk.sell_market_order(
                    ticker_id=ticker_id,
                    quant=position.quantity)
                self.print_log("🔴 Submit sell order <{}>[{}], quant: {}, latest close price: {}".format(
                    symbol, ticker_id, position.quantity, latest_close))
                # add swing trade
                # TODO, check order response object
                self.add_swing_trade(
                    symbol=symbol,
                    buy_order_id=position.order_id,
                    buy_price=position.cost,
                    quant=position.quantity,
                    buy_time=position.buy_time,
                    order_response=order_response)
                # clear position
                position.delete()
        else:
            # check if buy
            # get entry_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            latest_bar = hist_daily_bars.last()
            latest_close = latest_bar.close
            latest_sma120 = latest_bar.sma_120
            # make sure is uptrend
            if latest_close > latest_sma120:
                # get entry_period highest
                entry_period_highest = 0
                for i in range(len(hist_daily_bars) - self.entry_period - 1, len(hist_daily_bars) - 1):
                    daily_bar = hist_daily_bars[i]
                    if daily_bar.close > entry_period_highest:
                        entry_period_highest = daily_bar.close
                # check if entry_period new high
                if latest_close > entry_period_highest:
                    # buy swing position amount
                    buy_position_amount = self.get_buy_order_limit(symbol)
                    buy_quant = (int)(buy_position_amount / latest_close)
                    if buy_quant > 0:
                        ticker_id = webullsdk.get_ticker(symbol)
                        # submit market buy order
                        order_response = webullsdk.buy_market_order(
                            ticker_id=ticker_id,
                            quant=buy_quant)
                        self.print_log("🟢 Submit buy order <{}>[{}], quant: {}, latest close price: {}".format(
                            symbol, ticker_id, buy_quant, latest_close))
                        # add swing position
                        # TODO, check order response object
                        self.add_swing_position(symbol, order_response)

    def check_trading_hour(self):
        valid_time = True
        if datetime.now().hour < 9 or datetime.now().hour >= 16:
            # self.print_log("Skip pre and after market session, quit!")
            valid_time = False
        return valid_time

    def on_begin(self):

        if not self.check_trading_hour():
            return

        swing_watchlist = SwingWatchlist.objects.all()
        for swing_watch in swing_watchlist:
            symbol = swing_watch.symbol
            self.trading_symbols.append(symbol)

    def on_update(self):
        if not self.check_trading_hour():
            self.trading_end = False
            return

        # only trade regular market hour once
        if utils.is_regular_market_hour():

            # swing trading one symbol in each update
            if len(self.trading_symbols) > 0:
                symbol = self.trading_symbols[0]
                # swing trade using market order
                self.trade(symbol)
                # remove from swing_symbols
                del self.trading_symbols[0]

            # check if trading is end
            if len(self.trading_symbols) == 0:
                self.trading_end = True
