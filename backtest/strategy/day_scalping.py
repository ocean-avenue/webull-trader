# -*- coding: utf-8 -*-

from datetime import timedelta
from backtest.strategy.strategy_base import BacktestStrategyBase
from common.enums import SetupType
from common import config, constants, utils
from logger import trading_logger
from trading import pattern
from trading.tracker.trading_tracker import TrackingTicker


# Scalping day trade backtest class

class BacktestDayTradingScalping(BacktestStrategyBase):

    import pandas as pd
    from datetime import date
    from common.enums import SetupType, TradingHourType
    from typing import Tuple
    from trading.tracker.trading_tracker import TrackingTicker

    def __init__(self, trading_date: date, trading_hour: TradingHourType, entry_period: int = 20):
        super().__init__(trading_date=trading_date, trading_hour=trading_hour)
        self.entry_period: int = entry_period

    def get_tag(self) -> str:
        return "BacktestDayTradingScalping"

    def get_setup(self) -> SetupType:
        if self.entry_period == 30:
            return SetupType.DAY_30_CANDLES_NEW_HIGH
        elif self.entry_period == 20:
            return SetupType.DAY_20_CANDLES_NEW_HIGH
        return SetupType.DAY_10_CANDLES_NEW_HIGH

    # check if track in extended hour
    def check_surge(self, ticker: TrackingTicker, bar: pd.Series) -> bool:
        close = bar["close"]
        vwap = bar["vwap"]
        volume = int(bar["volume"])
        if close * volume >= config.MIN_SURGE_AMOUNT and volume >= config.MIN_SURGE_VOLUME and close > vwap:
            trading_logger.log(
                f"Found <{ticker.get_symbol()}> surge, price: {close}, volume: {volume}")
            return True
        return False

    def check_entry(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        symbol = ticker.get_symbol()
        current_candle = bars.iloc[-1]
        # use high for backtesting
        current_price = current_candle['high']
        # check if above vwap
        if current_price <= current_candle['vwap']:
            trading_logger.log(
                "<{}> price is not above vwap, no entry!".format(symbol))
            return False
        period_bars = bars.head(len(bars) - 1).tail(self.entry_period)
        period_high_price = 0
        period_low_price = constants.MAX_SECURITY_PRICE
        for _, row in period_bars.iterrows():
            # use close price for period high
            if row['close'] > period_high_price:
                period_high_price = row['close']
            # use low price for period low
            if row['low'] < period_low_price:
                period_low_price = row['low']

        # check if new high
        if current_price <= period_high_price:
            trading_logger.log(
                f"<{symbol}> price ${current_price} is not breakout high ${period_high_price}, no entry!")
            return False

        # check ema 9
        if current_price < current_candle['ema9']:
            trading_logger.log(
                "<{}> price is not above ema9, no entry!".format(symbol))
            return False

        # check if current low is above period low price
        current_low = current_candle['low']
        if current_low < period_low_price:
            trading_logger.log(
                "<{}> current low (${}) is lower than period low (${}), no entry!".format(symbol, current_low, period_low_price))
            return False

        # # check if gap already too large
        # if period_high_price * config.PERIOD_HIGH_PRICE_GAP_RATIO < current_price:
        #     trading_logger.log("<{}> new high price gap too large, new high: {}, period high: {}, no entry!".format(
        #         symbol, current_price, period_high_price))
        #     return False

        # check if current candle already surge too much
        prev_candle = bars.iloc[-2]
        prev_close = prev_candle['close']
        surge_ratio = (current_price - prev_close) / prev_close
        if surge_ratio >= config.MAX_DAY_ENTRY_CANDLE_SURGE_RATIO:
            trading_logger.log(
                f"<{symbol}> current price (${current_price}) already surge {round(surge_ratio * 100, 2)}% than prev close (${prev_close}), no entry!")
            return False

        if self.is_regular_market_hour() and not self.backtest_pattern.check_bars_updated(bars):
            trading_logger.log(
                "<{}> candle chart is not updated, stop trading!".format(symbol))
            # stop tracking
            self.trading_tracker.stop_tracking(ticker)
            return False

        if self.is_regular_market_hour() and not self.backtest_pattern.check_bars_continue(bars):
            trading_logger.log(
                "<{}> candle chart is not continue, stop trading!".format(symbol))
            # stop tracking
            self.trading_tracker.stop_tracking(ticker)
            return False

        if not pattern.check_bars_rel_volume(bars) and not self.backtest_pattern.check_bars_amount_grinding(bars, period=5) and \
                not pattern.check_bars_all_green(bars, period=5):
            # has no relative volume
            trading_logger.log(
                "<{}> candle chart has no relative volume, no entry!".format(symbol))
            return False

        if not self.backtest_pattern.check_bars_has_volume2(bars):
            # has no enough volume
            trading_logger.log(
                "<{}> candle chart has no enough volume, no entry!".format(symbol))
            return False

        if self.is_regular_market_hour() and not self.backtest_pattern.check_bars_volatility(bars):
            # no volatility
            trading_logger.log(
                "<{}> candle chart is not volatility, no entry!".format(symbol))
            return False

        if pattern.check_bars_has_long_wick_up(bars, period=self.entry_period):
            # has long wick up
            trading_logger.log(
                "<{}> candle chart has long wick up, no entry!".format(symbol))
            return False

        if not (self.backtest_pattern.check_bars_has_largest_green_candle(bars) and self.backtest_pattern.check_bars_has_more_green_candle(bars)) and \
                not self.backtest_pattern.check_bars_has_most_green_candle(bars):
            # not most green candles and no largest green candle
            trading_logger.log(
                "<{}> candle chart has no most green candles or largest candle is red, no entry!".format(symbol))
            return False

        if pattern.check_bars_has_bearish_candle(bars, period=5):
            # has bearish candle
            trading_logger.log(
                "<{}> candle chart has bearish candle, no entry!".format(symbol))
            return False

        ROC = self.get_price_rate_of_change(bars, period=self.entry_period)
        if ROC <= config.DAY_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            trading_logger.log(
                "<{}> candle chart price rate of change for {} period ({}) is weak, no entry!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        if ticker.get_last_sell_time() and (self.trading_time - ticker.get_last_sell_time()) <= timedelta(seconds=config.TRADE_INTERVAL_IN_SEC):
            trading_logger.log(
                "<{}> try buy too soon after last sell, no entry!".format(symbol))
            return False

        # for backtesting
        ticker.set_backtest_buy_price(round(period_high_price * 1.01, 2))

        return True

    def check_exit(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        symbol = ticker.get_symbol()
        exit_trading = False
        exit_note = None

        m2_bars = utils.convert_2m_bars(bars)
        # check if momentum is stop
        if pattern.check_bars_current_low_less_than_prev_low(m2_bars):
            trading_logger.log(
                f"<{symbol}> current low price is less than previous low price.")
            exit_trading = True
            exit_note = "Current Low < Previous Low."
        # check if has long wick up
        elif pattern.check_bars_has_long_wick_up(bars, period=5, count=2):
            trading_logger.log(
                "<{}> candle chart has long wick up, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart has long wick up."
        # check if bar chart has volatility
        elif self.is_extended_market_hour() and not self.backtest_pattern.check_bars_volatility(bars):
            trading_logger.log(
                "<{}> candle chart is not volatility, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is not volatility."
        # check if bar chart is at peak
        elif self.is_regular_market_hour() and pattern.check_bars_at_peak(bars):
            trading_logger.log(
                "<{}> candle chart is at peak, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is at peak."
        # check bar will reversal
        elif pattern.check_bars_reversal(bars):
            trading_logger.log(
                "<{}> candle chart will reversal, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart will reversal."

        if exit_trading:
            # for backtesting
            ticker.set_backtest_sell_price(bars.iloc[-1]['low'])

        return (exit_trading, exit_note)

    def check_stop_profit(self, ticker: TrackingTicker, position: dict) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate >= 1:
            exit_trading = True
            exit_note = "Home run at {}!".format(position['lastPrice'])
        ticker.set_backtest_sell_price(round(position['lastPrice'] * 0.99, 2))
        return (exit_trading, exit_note)

    def check_stop_loss(self, ticker: TrackingTicker, position: dict) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        # check stop loss
        if last_price < ticker.get_stop_loss():
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        ticker.set_backtest_sell_price(round(last_price * 0.99, 2))
        return (exit_trading, exit_note)

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        stop_loss = current_candle['low']
        if (current_price- current_candle['low']) / current_candle['low'] > 0.1:
            stop_loss = round(
                current_candle['low'] + (current_price- current_candle['low']) * 0.4, 2)
        # if stop loss is too tight
        if current_price * .98 < stop_loss:
            prev_candle = bars.iloc[-2]
            stop_loss_2 = prev_candle['low']
            if (prev_candle['high'] - prev_candle['low']) / prev_candle['low'] > 0.1:
                stop_loss_2 = round(
                    (prev_candle['high'] + prev_candle['low']) / 2, 2)
            stop_loss = min(stop_loss, stop_loss_2)
        return stop_loss

    def get_price_rate_of_change(self, bars: pd.DataFrame, period: int = 10) -> float:
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        period_price = period_bars.iloc[0]['close']
        current_price = bars.iloc[-1]['close']
        ROC = (current_price - period_price) / period_price * 100
        return ROC

    def trade(self, ticker: TrackingTicker, m1_bars: pd.DataFrame = pd.DataFrame()):

        ticker_id = ticker.get_id()
        symbol = ticker.get_symbol()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # fetch 1m bar charts
            if m1_bars.empty:
                m1_bars = self.backtest_df[symbol]
            if m1_bars.empty:
                return
            bars = m1_bars

            # calculate and fill ema 9 data
            bars['ema9'] = bars['close'].ewm(span=9, adjust=False).mean()

            # check entry: current price above vwap, entry period minutes new high
            if self.check_entry(ticker, bars):
                # set stop loss
                ticker.set_stop_loss(self.get_stop_loss_price(bars))
                # candle data
                current_candle = bars.iloc[-1]
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

            # check stop profit, home run
            exit_trading, exit_note = self.check_stop_profit(
                ticker, ticker_position)

            if not exit_trading:
                # get 1m bar charts
                # check_bars_at_peak require 30 bars
                m1_bars = self.backtest_df[symbol]
                # check bars error
                if m1_bars.empty:
                    trading_logger.log(
                        "<{}> bars data error!".format(symbol))
                    exit_trading = True
                    exit_note = "Bars data error!"

            if not exit_trading:
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(
                    ticker, ticker_position)

            if not exit_trading:
                bars = m1_bars
                trading_logger.log("Checking exit for <{}>, price: ${}, unrealized P&L: {}%".format(
                    symbol, bars.iloc[-1]['close'], round(profit_loss_rate * 100, 2)))
                # check exit trade
                exit_trading, exit_note = self.check_exit(ticker, bars)

            # exit trading
            if exit_trading:
                trading_logger.log(
                    f"📈 Exit trading <{symbol}> P&L: {round(profit_loss_rate * 100, 2)}%")

                self.submit_sell_limit_order(ticker, note=exit_note)

    def update(self):
        super().update()

        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        for backtest_ticker in self.backtest_tickers:
            symbol = backtest_ticker["symbol"]
            ticker_id = str(backtest_ticker["ticker_id"])
            # check if ticker already in tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            # init tracking ticker
            ticker = TrackingTicker(symbol, ticker_id)
            # check if can trade with requirements, skip check top 1 gainer
            if not self.check_can_trade_ticker(ticker):
                # trading_logger.log(
                #     "Can not trade <{}>, skip...".format(symbol))
                continue

            if self.is_extended_market_hour():
                m1_bars = self.backtest_df[symbol]
                if m1_bars.empty or len(m1_bars) < 2:
                    continue
                # use latest 2 candle
                latest_candle = m1_bars.iloc[-1]
                latest_candle2 = m1_bars.iloc[-2]
                # check if trasaction amount and volume meets requirement
                if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                    # update target units
                    ticker.set_target_units(
                        config.DAY_EXTENDED_TARGET_UNITS)
                    # start tracking ticker
                    self.trading_tracker.start_tracking(ticker)
                    trading_logger.log(
                        "Start trading <{}>...".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
            elif self.is_regular_market_hour():
                # update target units
                ticker.set_target_units(config.DAY_TARGET_UNITS)
                # start tracking ticker
                self.trading_tracker.start_tracking(ticker)
                trading_logger.log(
                    "Start trading <{}>...".format(symbol))
                # do trade
                self.trade(ticker)

    def end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()
