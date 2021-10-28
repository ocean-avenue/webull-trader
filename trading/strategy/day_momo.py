# -*- coding: utf-8 -*-

import math
import pandas as pd
from datetime import datetime, timedelta
from trading.strategy.strategy_base import StrategyBase
from common.enums import SetupType
from common import utils, config
from sdk import webullsdk
from logger import trading_logger
from trading import pattern
from trading.tracker.trading_tracker import TrackingTicker


# Momo day trading class

class DayTradingMomo(StrategyBase):

    import pandas as pd
    from typing import Tuple
    from common.enums import SetupType
    from trading.tracker.trading_tracker import TrackingTicker

    def get_tag(self) -> str:
        return "DayTradingMomo"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_FIRST_CANDLE_NEW_HIGH

    def check_track(self, bar: pd.Series) -> bool:
        close = bar["close"]
        vwap = bar["vwap"]
        volume = int(bar["volume"])
        if close * volume >= config.MIN_SURGE_AMOUNT and volume >= config.MIN_SURGE_VOLUME and close >= vwap:
            return True
        return False

    def check_entry_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        return True

    def check_entry(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        symbol = ticker.get_symbol()
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        # price data
        current_price = current_candle['close']
        prev_close = prev_candle['close']

        # check if current low is above prev close
        current_low = current_candle['low']
        prev_close = prev_candle['close']
        if current_low <= min(prev_close - 0.1, prev_close * 0.99):
            trading_logger.log(
                f"<{symbol}> current low (${current_low}) is lower than previous close (${prev_close}), no entry!")
            return False

        # # check if current candle already surge too much
        # if (current_price - prev_close) / prev_close >= config.MAX_DAY_ENTRY_CANDLE_SURGE_RATIO:
        #     surge_ratio = "{}%".format(
        #         round((current_price - prev_close) / prev_close * 100, 2))
        #     trading_logger.log(
        #         "<{}> current price (${}) already surge {} than prev close (${}), no entry!".format(symbol, current_price, surge_ratio, prev_close))
        #     return False

        if ticker.is_just_sold():
            trading_logger.log(
                "<{}> try buy too soon after last sell, no entry!".format(symbol))
            return False

        # check current price above vwap, ema9 and first candle make new high
        if current_price > current_candle['vwap'] and current_price > current_candle['ema9'] \
                and current_candle['high'] > prev_candle['high'] \
                and self.check_entry_extra(ticker, bars):
            return True

        return False

    def check_stop_loss(self, ticker: TrackingTicker, position: dict) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        # stop loss for buy prev low
        if last_price < ticker.get_stop_loss():
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        # stop loss for stop_loss_ratio
        elif profit_loss_rate <= self.stop_loss_ratio:
            exit_note = "Stop loss for {}%".format(
                round(profit_loss_rate * 100, 2))
            exit_trading = True
        return (exit_trading, exit_note)

    def check_exit(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        symbol = ticker.get_symbol()
        exit_trading = False
        exit_note = None
        # check if momentum is stop
        if pattern.check_bars_current_low_less_than_prev_low(bars):
            trading_logger.log(
                f"<{symbol}> current low price is less than previous low price.")
            exit_trading = True
            exit_note = "Current Low < Previous Low."
        return (exit_trading, exit_note)

    def trade(self, ticker: TrackingTicker, m1_bars: pd.DataFrame = pd.DataFrame()):

        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0 and ticker.is_tracking_timeout():
            trading_logger.log(
                "Trading <{}> session timeout!".format(symbol))
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            if m1_bars.empty:
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
            m2_bars = utils.convert_2m_bars(m1_bars)
            if m2_bars.empty:
                return

            current_price = m1_bars.iloc[-1]['close']

            if not pattern.check_bars_updated(m1_bars):
                trading_logger.log(
                    "<{}> candle chart is not updated, stop trading!".format(symbol))
                # stop tracking
                self.trading_tracker.stop_tracking(ticker)
                return

            if pattern.check_bars_has_long_wick_up(m1_bars, period=5, count=1):
                # has long wick up
                trading_logger.log(
                    "<{}> candle chart has long wick up, no entry!".format(symbol))
                return False

            # position size if buy
            pos_size = math.ceil(
                self.get_buy_order_limit(ticker) / current_price)
            if not pattern.check_bars_volume_with_pos_size(m1_bars, pos_size, period=10):
                # volume not enough for my position size
                trading_logger.log(
                    f"<{symbol}> candle chart volume is not enough for position size {pos_size}, no entry!")
                return False

            if not (pattern.check_bars_has_largest_green_candle(m1_bars) and pattern.check_bars_has_more_green_candle(m1_bars)) and \
                    not pattern.check_bars_has_most_green_candle(m1_bars):
                # not most green candles and no largest green candle
                trading_logger.log(
                    f"<{symbol}> candle chart has no most green candles or largest candle is red, no entry!")
                return False

            # if not pattern.check_bars_volatility(m1_bars):
            #     trading_logger.log("<{}> candle chart is not volatility, stop trading!".format(symbol))
            #     # remove from tracking
            #     self.trading_tracker.stop_tracking(ticker)
            #     return

            # check if last sell time is too short compare current time
            # if ticker.is_just_sold():
            #     trading_logger.log("Don't buy <{}> too quick after sold!".format(symbol))
            #     return

            # calculate and fill ema 9 data
            m2_bars['ema9'] = m2_bars['close'].ewm(span=9, adjust=False).mean()
            # candle data
            current_candle = m2_bars.iloc[-1]
            prev_candle = m2_bars.iloc[-2]

            # check entry: current price above vwap and ema 9, entry if first candle make new high
            if self.check_entry(ticker, m2_bars):
                # use prev low as stop loss
                ticker.set_stop_loss(prev_candle['low'])
                trading_logger.log("Trading <{}>, price: {}, vwap: {}, ema9: {}, volume: {}".format(
                    symbol, current_candle['close'], current_candle['vwap'], round(current_candle['ema9'], 3), int(current_candle['volume'])))
                # submit buy limit order
                self.submit_buy_limit_order(ticker)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                trading_logger.log(
                    "Finding <{}> position error!".format(symbol))
                return
            # cost = float(ticker_position['cost'])
            # last_price = float(ticker_position['lastPrice'])
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            ticker.set_last_profit_loss_rate(profit_loss_rate)
            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            if profit_loss_rate > ticker.get_max_profit_loss_rate():
                ticker.set_max_profit_loss_rate(profit_loss_rate)
            # quantity = int(ticker_position['position'])
            # trading_logger.log("Checking <{}>, cost: {}, last: {}, change: {}%".format(
            #     symbol, cost, last_price, round(profit_loss_rate * 100, 2)))

            # cancel buy prev low stop loss if hit 1% profit
            if profit_loss_rate >= 0.01:
                ticker.set_stop_loss(0)

            # check stop loss
            exit_trading, exit_note = self.check_stop_loss(
                ticker, ticker_position)

            # sell if drawdown 1% from max P&L rate
            # if ticker.get_max_profit_loss_rate() - profit_loss_rate >= 0.01:
            #     exit_trading = True

            # check if holding too long without profit
            if not exit_trading and ticker.is_holing_too_long() and profit_loss_rate < 0.01:
                trading_logger.log(
                    "Holding <{}> too long.".format(symbol))
                exit_note = "Holding too long."
                exit_trading = True

            if not exit_trading:
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=20)
                # get 2m bar charts
                m2_bars = utils.convert_2m_bars(m1_bars)

                # get bars error
                if m2_bars.empty:
                    trading_logger.log(
                        "<{}> bars data error!".format(symbol))
                    exit_note = "Bars data error!"
                    exit_trading = True
                else:

                    # check if price fixed in last 3 candles
                    if pattern.check_bars_price_fixed(m1_bars):
                        trading_logger.log(
                            f"<{symbol}> price is fixed during last 3 candles.")
                        exit_trading = True
                        exit_note = "Price fixed during last 3 candles."
                    # check if has long wick up
                    elif pattern.check_bars_has_long_wick_up(m1_bars, period=5, count=2):
                        trading_logger.log(
                            f"<{symbol}> candle chart has long wick up, exit!")
                        exit_trading = True
                        exit_note = "Candle chart has long wick up."
                    # check if bar chart is at peak
                    elif self.is_regular_market_hour() and pattern.check_bars_at_peak(m1_bars):
                        trading_logger.log(
                            f"<{symbol}> candle chart is at peak, exit!")
                        exit_trading = True
                        exit_note = "Candle chart is at peak."

                    # check exit trade
                    exit_trading, exit_note = self.check_exit(ticker, m2_bars)

            # exit trading
            if exit_trading:
                trading_logger.log(
                    f"📈 Exit trading <{symbol}> P&L: {round(profit_loss_rate * 100, 2)}%")

                self.submit_sell_limit_order(ticker, note=exit_note)

    def update(self):
        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if self.is_regular_market_hour():
            top_gainers = webullsdk.get_top_gainers()
        elif self.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif self.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # trading_logger.log("Scanning top gainers <{}>...".format(
        #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = str(gainer["ticker_id"])
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            ticker = TrackingTicker(symbol, ticker_id)
            # trading_logger.log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
                m2_bars = utils.convert_2m_bars(m1_bars)
                if m2_bars.empty or len(m2_bars) <= 2:
                    continue
                # use latest 2 candle
                latest_candle = m2_bars.iloc[-1]
                latest_candle2 = m2_bars.iloc[-2]
                # check if trasaction amount meets requirement
                if self.check_track(latest_candle) or self.check_track(latest_candle2):
                    # found trading ticker
                    self.trading_tracker.start_tracking(ticker)
                    trading_logger.log(
                        "Start trading <{}>...".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)

    def end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

    def final(self):

        # cancel all existing order
        webullsdk.cancel_all_orders()

        # track failed to sell positions
        self.track_rest_positions()


# Momo day trading with same share size

class DayTradingMomoShareSize(DayTradingMomo):

    SHARE_SIZE = 100

    def get_tag(self) -> str:
        return "DayTradingMomoShareSize"

    def get_buy_order_limit(self, ticker: TrackingTicker):
        buy_position_amount = super().get_buy_order_limit()
        symbol = ticker.get_symbol()
        tracking_stat = self.trading_tracker.get_stat(symbol)
        trades_count = tracking_stat.get_trades()
        # check win rate
        if trades_count > 0:
            win_rate = float(tracking_stat.get_win_trades()) / trades_count
            buy_position_amount = buy_position_amount * max(win_rate, 0.3)
        return buy_position_amount

    def submit_buy_limit_order(self, ticker: TrackingTicker, note: str = "Entry point."):
        from common import db
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        buy_price = self.get_buy_price(ticker)
        buy_position_amount = buy_price * self.SHARE_SIZE
        if usable_cash <= buy_position_amount:
            trading_logger.log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_quant = (int)(buy_position_amount / buy_price)
        if buy_quant > 0:
            # submit limit order at ask price
            order_response = webullsdk.buy_limit_order(
                ticker_id=ticker_id,
                price=buy_price,
                quant=buy_quant)
            order_id = utils.get_order_id_from_response(
                order_response, paper=self.paper)
            if order_id:
                trading_logger.log(
                    f"🟢 Submit buy order {order_id}, ticker: <{symbol}>, quant: {buy_quant}, limit price: {buy_price}")
                # tracking pending buy order
                self.start_tracking_pending_buy_order(
                    ticker, order_id, entry_note=note)
            else:
                trading_logger.log(
                    f"⚠️  Invalid buy order response: {order_response}")
        else:
            trading_logger.log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))


# Momo day trading based on win rate, reduce size if win rate is low

class DayTradingMomoReduceSize(DayTradingMomo):

    def get_tag(self) -> str:
        return "DayTradingMomoReduceSize"

    def get_buy_order_limit(self, ticker: TrackingTicker):
        buy_position_amount = super().get_buy_order_limit()
        symbol = ticker.get_symbol()
        tracking_stat = self.trading_tracker.get_stat(symbol)
        trades_count = tracking_stat.get_trades()
        # check win rate
        if trades_count > 0:
            win_rate = float(tracking_stat.get_win_trades()) / trades_count
            buy_position_amount = buy_position_amount * max(win_rate, 0.3)
        return buy_position_amount

    def check_entry_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        return not self.check_if_3_continue_loss_trades(ticker)

    def check_if_3_continue_loss_trades(self, ticker: TrackingTicker) -> bool:
        symbol = ticker.get_symbol()
        tracking_stat = self.trading_tracker.get_stat(symbol)
        continue_lose_trades = tracking_stat.get_continue_lose_trades()
        if continue_lose_trades >= 3 and (datetime.now() - tracking_stat.get_last_trade_time()) <= timedelta(seconds=config.BLACKLIST_TIMEOUT_IN_SEC):
            return True
        return False


# Momo day trade, no entry if the price not break max of last high price.

class DayTradingMomoNewHigh(DayTradingMomo):

    def get_tag(self) -> str:
        return "DayTradingMomoNewHigh"

    def check_entry_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:

        current_price = bars.iloc[-1]['close']
        return self.check_if_trade_price_reach_new_high(ticker, current_price)

    def check_if_trade_price_reach_new_high(self, ticker: TrackingTicker, price: float) -> bool:
        symbol = ticker.get_symbol()
        tracking_stat = self.trading_tracker.get_stat(symbol)
        last_high_price = tracking_stat.get_last_high_price()
        if last_high_price != None:
            return price > last_high_price
        return True


# Momo day trading class, only trade in extended hour (include new high condition)

class DayTradingMomoExtendedHour(DayTradingMomo):

    def get_tag(self) -> str:
        return "DayTradingMomoExtendedHour"

    def check_entry_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:

        current_price = bars.iloc[-1]['close']
        return self.check_if_trade_price_reach_new_high(ticker, current_price)

    def check_if_trade_price_reach_new_high(self, ticker: TrackingTicker, price: float) -> bool:
        symbol = ticker.get_symbol()
        tracking_stat = self.trading_tracker.get_stat(symbol)
        last_high_price = tracking_stat.get_last_high_price()
        if last_high_price != None:
            return price > last_high_price
        return True

    def update(self):

        # only trading in extended hour
        if self.is_regular_market_hour():
            self.trading_end = True
            return

        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if self.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif self.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # trading_logger.log("Scanning top gainers <{}>...".format(
        #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = str(gainer["ticker_id"])
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            ticker = TrackingTicker(symbol, ticker_id)
            # trading_logger.log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
                m2_bars = utils.convert_2m_bars(m1_bars)
                if m2_bars.empty:
                    continue
                # use latest 2 candle
                latest_candle = m2_bars.iloc[-1]
                latest_candle2 = m2_bars.iloc[-2]
                # check if trasaction amount meets requirement
                if self.check_track(latest_candle) or self.check_track(latest_candle2):
                    # found trading ticker
                    self.trading_tracker.start_tracking(ticker)
                    trading_logger.log(
                        "Start trading <{}>...".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
