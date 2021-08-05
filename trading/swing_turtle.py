# -*- coding: utf-8 -*-

# Turtle trading

from datetime import date
from django.utils import timezone
from trading.strategy_base import StrategyBase
from webull_trader.enums import ActionType, SetupType
from webull_trader.models import ManualTradeRequest, StockQuote, SwingHistoricalDailyBar, SwingPosition, SwingWatchlist
from sdk import webullsdk
from scripts import utils, config


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

    def get_buy_order_limit(self, unit_weight):
        return self.swing_position_amount_limit * unit_weight

    def check_has_volume(self, daily_bars):
        if not utils.check_daily_bars_volume_grinding(daily_bars, period=5) and \
                not utils.check_daily_bars_rel_volume(daily_bars):
            return False
        return True

    def check_period_high(self, daily_bars):
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

    def check_period_low(self, daily_bars):
        if len(daily_bars) <= self.exit_period:
            return False
        latest_close = daily_bars[-1].close
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

    def submit_buy_order(self, symbol, position, unit_weight, latest_close, reason):
        usable_cash = webullsdk.get_usable_cash()
        # buy swing position amount
        buy_position_amount = self.get_buy_order_limit(unit_weight)
        if usable_cash <= buy_position_amount:
            utils.print_trading_log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_quant = (int)(buy_position_amount / latest_close)
        # make sure usable cash is enough
        if buy_quant > 0 and usable_cash > self.day_trade_usable_cash_threshold:
            ticker_id = webullsdk.get_ticker(symbol)
            # submit market buy order
            order_response = webullsdk.buy_market_order(
                ticker_id=ticker_id,
                quant=buy_quant)
            utils.print_trading_log("🟢 Submit buy order <{}> for {}, quant: {}, latest price: {}".format(
                symbol, reason, buy_quant, latest_close))
            # add swing position
            self.update_pending_swing_position(
                symbol,
                order_response,
                position=position,
                cost=latest_close,
                quant=buy_quant,
                buy_time=timezone.now(),
                setup=self.get_setup())
        else:
            if buy_quant == 0:
                utils.print_trading_log(
                    "Order amount limit not enough for to buy <{}>, price: {}".format(symbol, latest_close))
            if usable_cash <= self.day_trade_usable_cash_threshold:
                utils.print_trading_log(
                    "Not enough cash for day trade threshold, skip <{}>, price: {}".format(symbol, latest_close))

    def submit_sell_order(self, symbol, position, latest_close, reason):
        ticker_id = webullsdk.get_ticker(symbol)
        # submit market sell order
        order_response = webullsdk.sell_market_order(
            ticker_id=ticker_id,
            quant=position.quantity)
        utils.print_trading_log("🔴 Submit sell order <{}> for {}, quant: {}, latest price: {}".format(
            symbol, reason, position.quantity, latest_close))
        # add swing trade
        self.update_pending_swing_trade(
            symbol=symbol,
            order_response=order_response,
            position=position,
            price=latest_close,
            sell_time=timezone.now())

    def trade(self, watchlist):
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
                self.submit_sell_order(
                    symbol, position, latest_close, "period low")
            elif latest_close < position.stop_loss_price:  # check if stop loss
                self.submit_sell_order(
                    symbol, position, latest_close, "stop loss")
            elif latest_close > position.add_unit_price:  # check if add unit
                self.submit_buy_order(
                    symbol, position, unit_weight, latest_close, "add unit")
        else:
            # check if buy
            # get entry_period+1 daily bars
            hist_daily_bars = SwingHistoricalDailyBar.objects.filter(
                symbol=symbol)
            current_daily_bars = list(hist_daily_bars)
            # prev_daily_bars = current_daily_bars[0:len(current_daily_bars)-1]
            if len(current_daily_bars) <= self.entry_period:
                utils.print_trading_log(
                    "<{}> daily chart has not enough data, no entry!".format(symbol))
            # check daily bars has volume
            elif not self.check_has_volume(current_daily_bars):
                utils.print_trading_log(
                    "<{}> daily chart has not enough volume, no entry!".format(symbol))
            # check period high for entry
            else:
                if self.check_period_high(current_daily_bars):
                    latest_close = current_daily_bars[-1].close
                    self.submit_buy_order(
                        symbol, None, unit_weight, latest_close, "period high")

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
                utils.print_trading_log("🔴 Submit manual sell order <{}>, quant: {}, latest price: {}".format(
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
                utils.print_trading_log("Unable to find match position <{}>, quant: {} for sell manual request.".format(
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
                "unit_weight": swing_watch.unit_weight,
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
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())
