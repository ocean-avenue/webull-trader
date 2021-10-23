# -*- coding: utf-8 -*-

import pandas as pd
from typing import Tuple
from trading.strategy.strategy_base import StrategyBase
from common.enums import SetupType, TradingHourType
from common import utils, constants
from logger import trading_logger
from sdk import webullsdk, finvizsdk
from trading.tracker.trading_tracker import TrackingTicker


# VWAP reclaim day trading strategy


# OTOCO order is not available in paper account
class DayTradingVWAPPaper(StrategyBase):

    def __init__(self, paper: bool, trading_hour: TradingHourType):
        super().__init__(paper=paper, trading_hour=trading_hour)

    def get_tag(self) -> str:
        return "DayTradingVWAP"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_VWAP_RECLAIM

    # return (SHOULD_ENTRY, TARGET_PROFIT, STOP_LOSS)
    def check_entry(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, float, float]:
        # check if have prev candles below vwap
        below_vwap_count = 0
        period_high = 0
        period_low = constants.MAX_SECURITY_PRICE
        for _, candle in bars.iterrows():
            if candle['low'] < candle['vwap']:
                below_vwap_count += 1
            if candle['close'] > period_high:
                period_high = candle['close']
            if candle['low'] < period_low:
                period_low = candle['low']
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        # min stop loss 2%
        period_low = min(round(current_price * 0.98, 2), period_low)
        current_vwap = current_candle['vwap']
        below_vwap_percent = below_vwap_count / len(bars)
        # check if current price above vwap, prev price below vwap and below vwap percentage <= 40%
        if current_price > current_vwap and below_vwap_count > 0 and below_vwap_percent <= 0.4:
            # check if profit/loss ratio is over 2
            if (period_high - current_price) / (current_price - period_low) >= 2.0:
                return (True, period_high, period_low)
        return (False, 0.0, 0.0)

    def check_stop_loss(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        stop_loss = ticker.get_stop_loss()
        for _, candle in bars.iterrows():
            # check if latest low is lower than stop loss
            if candle['low'] < stop_loss:
                exit_trading = True
                exit_note = "Price (${}) below stop loss (${})!".format(
                    candle['low'], stop_loss)
                break
        return (exit_trading, exit_note)

    def check_exit(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        symbol = ticker.get_symbol()
        exit_trading = False
        exit_note = None
        target_profit = ticker.get_target_profit()
        for _, candle in bars.iterrows():
            # check if price already reach target profit
            if candle['high'] >= target_profit:
                exit_trading = True
                exit_note = "Price (${}) reach target profit (${}).".format(
                    candle['high'], target_profit)
                trading_logger.log("<{}> price (${}) is reach target profit (${}), exit!".format(
                    symbol, candle['high'], target_profit))
                break

        return (exit_trading, exit_note)

    def trade(self, ticker: TrackingTicker):

        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()

        if holding_quantity == 0:
            # fetch 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=30)
            if m1_bars.empty:
                return
            bars = m1_bars

            # candle data
            current_candle = bars.iloc[-1]

            should_entry, target_profit, stop_loss = self.check_entry(
                ticker, bars)
            # check entry: current above vwap
            if should_entry:
                trading_logger.log("Trading <{}>, price: {}, vwap: {}, volume: {}".format(
                    symbol, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                # set target profit
                ticker.set_target_profit(target_profit)
                # set stop loss
                ticker.set_stop_loss(stop_loss)
                # submit buy limit order
                self.submit_buy_limit_order(ticker)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                trading_logger.log(
                    "Finding <{}> position error!".format(symbol))
                return
            if holding_quantity <= 0:
                # position is negitive, some unknown error happen
                trading_logger.log("<{}> holding quantity is negitive {}!".format(
                    symbol, holding_quantity))
                self.trading_tracker.stop_tracking(ticker)
                return

            # get 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=5)

            # get bars error
            if m1_bars.empty:
                trading_logger.log("<{}> bars data error!".format(symbol))
                exit_trading = True
                exit_note = "Bars data error!"
            else:
                profit_loss_rate = float(
                    ticker_position['unrealizedProfitLossRate'])
                ticker.set_last_profit_loss_rate(profit_loss_rate)

                bars = m1_bars
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(ticker, bars)
                # check exit trade
                if not exit_trading:
                    trading_logger.log("Checking exit for <{}>, unrealized P&L: {}%".format(
                        symbol, round(profit_loss_rate * 100, 2)))
                    exit_trading, exit_note = self.check_exit(ticker, bars)

                # exit trading
                if exit_trading:
                    self.submit_sell_limit_order(
                        ticker, note=exit_note, retry=True, retry_limit=50)

    def update(self):
        # trading tickers
        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
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

        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = str(gainer["ticker_id"])
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            # init tracking ticker
            ticker = TrackingTicker(symbol, ticker_id)
            # check if can trade with requirements
            if not self.check_can_trade_ticker(ticker):
                # trading_logger.log(
                #     "Can not trade <{}>, skip...".format(symbol))
                continue
            # start tracking
            self.trading_tracker.start_tracking(ticker)
            # do trade
            self.trade(ticker)

    def end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

    def final(self):

        # track failed to sell positions
        self.track_rest_positions()


class DayTradingVWAPLargeCap(StrategyBase):

    def __init__(self, paper: bool, trading_hour: TradingHourType):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.large_cap_with_major_news = {}

    def get_tag(self) -> str:
        return "DayTradingVWAPLargeCap"

    def get_setup(self) -> SetupType:
        return SetupType.DAY_VWAP_RECLAIM

    def check_entry(self, ticker: TrackingTicker, bars: pd.DataFrame):
        # check if have prev candles below vwap
        has_candle_below_vwap = False
        for _, candle in bars.iterrows():
            if candle['close'] < candle['vwap']:
                has_candle_below_vwap = True
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        current_vwap = current_candle['vwap']
        # check if current price above vwap and prev price below vwap
        if current_price > current_vwap and has_candle_below_vwap:
            return True
        return False

    def check_stop_loss(self, ticker: TrackingTicker, bars: pd.DataFrame):
        exit_trading = False
        exit_note = None
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        current_vwap = current_candle['vwap']
        # check if current price below vwap
        if current_price < current_vwap:
            exit_trading = True
            exit_note = "Stop loss, price ({}) below vwap ({})!".format(
                current_price, current_vwap)
        return (exit_trading, exit_note)

    def check_exit(self, ticker: TrackingTicker, bars: pd.DataFrame):
        symbol = ticker.get_symbol()
        exit_trading = False
        exit_note = None
        exit_period = 10
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        period_bars = bars.head(len(bars) - 1).tail(exit_period)
        period_low_price = constants.MAX_SECURITY_PRICE
        for _, row in period_bars.iterrows():
            close_price = row['close']
            if close_price < period_low_price:
                period_low_price = close_price
        # check if new low
        if current_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(exit_period)
            trading_logger.log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, current_price, period_low_price))

        return (exit_trading, exit_note)

    def trade(self, ticker: TrackingTicker):

        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)

        holding_quantity = ticker.get_positions()

        if holding_quantity == 0:
            # fetch 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=15)
            if m1_bars.empty:
                return
            bars = m1_bars

            # candle data
            current_candle = bars.iloc[-1]

            # check entry: current above vwap
            if self.check_entry(ticker, bars):
                trading_logger.log("Trading <{}>, price: {}, vwap: {}, volume: {}".format(
                    symbol, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                # submit buy limit order
                self.submit_buy_limit_order(ticker)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                trading_logger.log(
                    "Finding <{}> position error!".format(symbol))
                return
            if holding_quantity <= 0:
                # position is negitive, some unknown error happen
                trading_logger.log("<{}> holding quantity is negitive {}!".format(
                    symbol, holding_quantity))
                self.trading_tracker.stop_tracking(ticker)
                return

            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            ticker.set_last_profit_loss_rate(profit_loss_rate)

            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            if profit_loss_rate > ticker.get_max_profit_loss_rate():
                ticker.set_max_profit_loss_rate(profit_loss_rate)

            # get 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=15)
            # get bars error
            if m1_bars.empty:
                trading_logger.log("<{}> bars data error!".format(symbol))
                exit_trading = True
                exit_note = "Bars data error!"
            else:
                bars = m1_bars
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(ticker, bars)
                # check exit trade
                if not exit_trading:
                    # check exit trade
                    trading_logger.log("Checking exit for <{}>, unrealized P&L: {}%".format(
                        symbol, round(profit_loss_rate * 100, 2)))
                    exit_trading, exit_note = self.check_exit(ticker, bars)

            # exit trading
            if exit_trading:
                # submit sell limit order
                self.submit_sell_limit_order(
                    ticker, note=exit_note, retry=True, retry_limit=50)

    def update(self):
        # trading tickers
        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
            # do trade
            self.trade(ticker)

        # find large cap ticker with major news
        large_cap_with_major_news = finvizsdk.fetch_screeners(
            finvizsdk.MAJOR_NEWS_SCREENER)

        for large_cap in large_cap_with_major_news:
            symbol = large_cap["symbol"]
            # already exist in watchlist
            if symbol in self.large_cap_with_major_news:
                continue
            ticker_id = str(webullsdk.get_ticker(symbol=symbol))
            self.large_cap_with_major_news[symbol] = {
                "symbol": symbol,
                "ticker_id": ticker_id,
            }
            trading_logger.log(
                "Found ticker <{}> to check reclaim vwap!".format(symbol))

        for symbol in list(self.large_cap_with_major_news):
            ticker_id = self.large_cap_with_major_news[symbol]["ticker_id"]
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            # init tracking ticker
            ticker = TrackingTicker(symbol, ticker_id)
            # add to tracking
            self.trading_tracker.start_tracking(ticker)
            # do trade
            self.trade(ticker)

    def end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

    def final(self):

        # track failed to sell positions
        self.track_rest_positions()
