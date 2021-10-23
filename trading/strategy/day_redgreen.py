# -*- coding: utf-8 -*-

from datetime import datetime
from trading.strategy.strategy_base import StrategyBase
from common.enums import SetupType
from common import utils, config
from sdk import webullsdk
from trading import pattern
from trading.tracker.trading_tracker import TrackingTicker
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser


# Red to green day trading class

class DayTradingRedGreen(StrategyBase):

    def get_tag(self) -> str:
        return "DayTradingRedGreen"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker: TrackingTicker):

        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()

        if ticker.is_pending_buy():
            self.check_buy_order_done(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_done(
                ticker, stop_tracking_ticker_after_order_filled=False)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

        prev_day_close = ticker.get_prev_close()
        prev_day_high = ticker.get_prev_high()
        holding_quantity = ticker.get_positions()

        # fetch 1m bar charts
        m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
        m2_bars = utils.convert_2m_bars(m1_bars)
        if m2_bars.empty:
            return

        current_candle = m2_bars.iloc[-1]
        prev_candle = m2_bars.iloc[-2]

        # current price data
        current_high = current_candle['high']
        current_low = current_candle['low']
        prev_low = prev_candle['low']

        if holding_quantity == 0:

            if not pattern.check_bars_updated(m2_bars):
                utils.print_trading_log(
                    "<{}> candle chart is not updated, stop trading!".format(symbol))
                # remove from tracking
                self.trading_tracker.stop_tracking(ticker)
                return

            if not utils.check_bars_has_volume(m2_bars, time_scale=2):
                utils.print_trading_log(
                    "<{}> candle chart has not enough volume, stop trading!".format(symbol))
                # remove from tracking
                self.trading_tracker.stop_tracking(ticker)
                return

            if not utils.check_bars_rel_volume(m2_bars):
                utils.print_trading_log(
                    "<{}> candle chart has no relative volume, stop trading!".format(symbol))
                # remove from tracking
                self.trading_tracker.stop_tracking(ticker)
                return

            now = datetime.now()

            # check entry, current price above prev day close with (prev price below or not long after market open)
            if current_low >= prev_day_close and (prev_low <= prev_day_close or (now - datetime(now.year, now.month, now.day, 9, 30)).seconds <= 300):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                ask_price = webullsdk.get_ask_price_from_quote(quote)
                if ask_price == None:
                    return
                # check if ask_price is too high above prev day close
                if (ask_price - prev_day_close) / prev_day_close > config.MAX_PREV_DAY_CLOSE_GAP_RATIO:
                    utils.print_trading_log("<{}> gap too large, ask: {}, prev day close: {}, stop trading!".format(
                        symbol, ask_price, prev_day_close))
                    return
                # use prev day close as stop loss
                ticker.set_stop_loss(prev_day_close)
                # use prev day high as target profit
                ticker.set_target_profit(prev_day_high)
                # submit buy limit order
                self.submit_buy_limit_order(ticker)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                utils.print_trading_log(
                    "Finding <{}> position error!".format(symbol))
                return
            # profit loss rate
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            ticker.set_last_profit_loss_rate(profit_loss_rate)
            # check if exit trading
            exit_trading = False
            last_price = float(ticker_position['lastPrice'])
            # check stop loss, prev day close
            if current_high < ticker.get_stop_loss():
                exit_note = "Stop loss at {}!".format(last_price)
                exit_trading = True
            # check taking profit, current price above prev day high
            if last_price >= ticker.get_target_profit():
                exit_note = "Take profit at {}!".format(last_price)
                exit_trading = True
            # exit trading
            if exit_trading:
                utils.print_trading_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                self.submit_sell_limit_order(
                    ticker, note=exit_note, retry=True, retry_limit=50)

    def begin(self):

        if not self.is_regular_market_hour():
            return

        # default today
        last_market_day = datetime.today().date()
        first_gainer = HistoricalTopGainer.objects.last()
        if first_gainer:
            last_market_day = first_gainer.date

        # hist top gainers
        top_gainers = HistoricalTopGainer.objects.filter(date=last_market_day)
        # update tracking tickers
        for gainer in top_gainers:
            gainer: HistoricalTopGainer = gainer
            symbol = gainer.symbol
            ticker_id = gainer.ticker_id
            quote = webullsdk.get_quote(ticker_id=ticker_id)
            if 'open' in quote:
                # weak open
                if float(quote['open']) <= gainer.price:
                    key_stat = utils.get_hist_key_stat(symbol, last_market_day)
                    ticker = TrackingTicker(symbol, ticker_id)
                    ticker.set_prev_close(gainer.price)
                    ticker.set_prev_high(key_stat.high)
                    # start tracking
                    self.trading_tracker.start_tracking(ticker)
                    utils.print_trading_log(
                        "Add gainer <{}> to trade!".format(symbol))
            else:
                utils.print_trading_log(
                    "Cannot find <{}> open price!".format(symbol))
        # hist top losers
        top_losers = HistoricalTopLoser.objects.filter(date=last_market_day)
        # update tracking tickers
        for loser in top_losers:
            loser: HistoricalTopLoser = loser
            symbol = loser.symbol
            ticker_id = loser.ticker_id
            quote = webullsdk.get_quote(ticker_id=ticker_id)
            if 'open' in quote:
                # weak open
                if float(quote['open']) <= loser.price:
                    key_stat = utils.get_hist_key_stat(symbol, last_market_day)
                    ticker = TrackingTicker(symbol, ticker_id)
                    ticker.set_prev_close(loser.price)
                    ticker.set_prev_high(key_stat.high)
                    # start tracking
                    self.trading_tracker.start_tracking(ticker)
                    utils.print_trading_log(
                        "Add loser <{}> to trade!".format(symbol))
            else:
                utils.print_trading_log(
                    "Cannot find <{}> open price!".format(symbol))

    def is_power_hour(self) -> bool:
        now = datetime.now()
        if now.hour <= 12:
            return True
        return False

    def update(self):
        if not self.is_regular_market_hour():
            self.trading_end = False
            return

        # only trade regular market hour before 13:00
        if self.is_power_hour():
            # trading tickers
            for symbol in self.trading_tracker.get_tickers():
                ticker = self.trading_tracker.get_ticker(symbol)
                # do trade
                self.trade(ticker)
        else:
            self.trading_end = True

    def end(self):
        self.trading_end = True
        # check if still holding any positions before exit
        self.clear_positions()

    def final(self):

        # track failed to sell positions
        self.track_rest_positions()
