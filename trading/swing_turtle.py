# -*- coding: utf-8 -*-

# Turtle trading

from datetime import date
from django.utils import timezone
from trading.strategy_base import StrategyBase
from webull_trader.enums import ActionType, SetupType
from webull_trader.models import ManualTradeRequest, StockQuote, SwingHistoricalDailyBar, SwingPosition, SwingWatchlist
from sdk import webullsdk
from scripts import utils


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
                self.print_log("🔴 Submit sell order <{}>, quant: {}, latest price: {}".format(
                    symbol, position.quantity, latest_close))
                # add swing trade
                self.update_pending_swing_trade(
                    symbol=symbol,
                    order_response=order_response,
                    position=position,
                    price=latest_close,
                    sell_time=timezone.now())
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
                usable_cash = webullsdk.get_usable_cash()
                buy_position_amount = self.get_buy_order_limit(units)
                if usable_cash <= buy_position_amount:
                    self.print_log(
                        "Not enough cash to buy <{}>, price: {}!".format(symbol, latest_close))
                    return
                buy_quant = (int)(buy_position_amount / latest_close)
                # make sure usable cash is enough
                if buy_quant > 0 and usable_cash > self.day_trade_usable_cash_threshold:
                    ticker_id = webullsdk.get_ticker(symbol)
                    # submit market buy order
                    order_response = webullsdk.buy_market_order(
                        ticker_id=ticker_id,
                        quant=buy_quant)
                    self.print_log("🟢 Submit buy order <{}>, quant: {}, latest price: {}".format(
                        symbol, buy_quant, latest_close))
                    # add swing position
                    self.update_pending_swing_position(
                        symbol,
                        order_response,
                        cost=latest_close,
                        quant=buy_quant,
                        buy_time=timezone.now(),
                        setup=self.get_setup())
                else:
                    if buy_quant == 0:
                        self.print_log(
                            "Order amount limit not enough for to buy <{}>, price: {}".format(symbol, latest_close))
                    if usable_cash <= self.day_trade_usable_cash_threshold:
                        self.print_log(
                            "Not enough cash for day trade threshold, skip <{}>, price: {}".format(symbol, latest_close))

    def manual_trade(self, request):
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
                ticker_id = webullsdk.get_ticker(symbol)
                latest_price = 0.0
                quote = StockQuote.objects.filter(symbol=symbol).first()
                if quote:
                    latest_price = quote.price
                # submit market sell order
                order_response = webullsdk.sell_market_order(
                    ticker_id=ticker_id,
                    quant=quantity)
                self.print_log("🔴 Submit manual sell order <{}>, quant: {}, latest price: {}".format(
                    symbol, quantity, latest_price))
                # add swing trade
                self.update_pending_swing_trade(
                    symbol=symbol,
                    order_response=order_response,
                    position=position,
                    price=latest_price,
                    sell_time=timezone.now(),
                    manual_request=request)
            else:
                self.print_log("Unable to find match position <{}>, quant: {} for sell manual request.".format(
                    symbol, quantity))
        # mark request done
        request.complete = True
        request.save()

    def on_begin(self):
        # only trade regular market hour once
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
            return

        # manual request first
        manual_request = ManualTradeRequest.objects.filter(
            setup=self.get_setup(), complete=False).first()
        if manual_request:
            self.manual_trade(manual_request)
            return

        # swing trading one symbol in each update
        if len(self.trading_watchlist) > 0:
            watchlist = self.trading_watchlist[0]
            # swing trade using market order
            self.trade(watchlist)
            # remove from swing_symbols
            del self.trading_watchlist[0]

    def on_end(self):
        self.trading_end = True

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.trading_hour, date.today())
