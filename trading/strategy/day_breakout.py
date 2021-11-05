# -*- coding: utf-8 -*-

import math
import pandas as pd
from datetime import datetime, date, timedelta
from common.enums import SetupType, TradingHourType
from typing import List, Optional, Tuple
from common import utils, config, constants
from sdk import webullsdk
from logger import trading_logger
from trading import pattern
from trading.strategy.strategy_base import StrategyBase
from trading.tracker.trading_tracker import TrackingTicker
from webull_trader.models import EarningCalendar


# Breakout day trading class

class DayTradingBreakout(StrategyBase):

    import pandas as pd
    from common.enums import SetupType, TradingHourType
    from typing import Tuple
    from trading.tracker.trading_tracker import TrackingTicker

    def __init__(self, paper: bool, trading_hour: TradingHourType, entry_period: int = 20, exit_period: int = 10, time_scale: int = 1):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.entry_period: int = entry_period
        self.exit_period: int = exit_period
        self.time_scale: int = time_scale

    def get_tag(self) -> str:
        return "DayTradingBreakout"

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

    def check_entry_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        return True

    def check_entry(self, ticker: TrackingTicker, bars: pd.DataFrame) -> bool:
        symbol = ticker.get_symbol()
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
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

        # additional check in subclass
        if not self.check_entry_extra(ticker, bars):
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

        if self.is_regular_market_hour() and not pattern.check_bars_updated(bars):
            trading_logger.log(
                "<{}> candle chart is not updated, stop trading!".format(symbol))
            # stop tracking
            self.trading_tracker.stop_tracking(ticker)
            return False

        if self.is_regular_market_hour() and not pattern.check_bars_continue(bars, time_scale=self.time_scale):
            trading_logger.log(
                "<{}> candle chart is not continue, stop trading!".format(symbol))
            # stop tracking
            self.trading_tracker.stop_tracking(ticker)
            return False

        if not pattern.check_bars_rel_volume(bars) and not pattern.check_bars_amount_grinding(bars, period=5) and \
                not pattern.check_bars_all_green(bars, period=5):
            # has no relative volume
            trading_logger.log(
                "<{}> candle chart has no relative volume, no entry!".format(symbol))
            return False

        if not pattern.check_bars_has_volume2(bars):
            # has no enough volume
            trading_logger.log(
                "<{}> candle chart has no enough volume, no entry!".format(symbol))
            return False

        if self.is_regular_market_hour() and not pattern.check_bars_volatility(bars):
            # no volatility
            trading_logger.log(
                "<{}> candle chart is not volatility, no entry!".format(symbol))
            return False

        if pattern.check_bars_has_long_wick_up(bars, period=self.entry_period):
            # has long wick up
            trading_logger.log(
                "<{}> candle chart has long wick up, no entry!".format(symbol))
            return False

        if not (pattern.check_bars_has_largest_green_candle(bars) and pattern.check_bars_has_more_green_candle(bars)) and \
                not pattern.check_bars_has_most_green_candle(bars):
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

        if ticker.is_just_sold():
            trading_logger.log(
                "<{}> try buy too soon after last sell, no entry!".format(symbol))
            return False

        return True

    def check_exit_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        return (False, None)

    def check_exit(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        symbol = ticker.get_symbol()
        exit_period = ticker.get_exit_period() or self.exit_period
        # latest candle
        current_candle = bars.iloc[-1]
        last_candle = bars.iloc[-2]
        current_candle_time = bars.index[-1].to_pydatetime()
        last_buy_time = ticker.get_last_buy_time()
        # align timezone info
        last_buy_time = last_buy_time.replace(
            tzinfo=current_candle_time.tzinfo)
        # make sure last formed candle is not same as buy candle
        if last_buy_time > current_candle_time:
            if ((last_buy_time - current_candle_time).seconds//60) % 60 == 0:
                return (False, None)
        else:
            if ((current_candle_time - last_buy_time).seconds//60) % 60 == 0:
                return (False, None)
        exit_trading = False
        exit_note = None
        current_price = current_candle['close']
        last_price = last_candle['close']
        period_bars = bars.head(len(bars) - 2).tail(exit_period)
        period_low_price = constants.MAX_SECURITY_PRICE
        period_low_idx = -1
        for i in range(0, len(period_bars)):
            close_price = period_bars.iloc[i].close
            if close_price < period_low_price:
                period_low_price = close_price
                period_low_idx = i
        if period_low_idx < len(period_bars) - 1:
            # add 1% threshold
            threshold = 0.01
            period_low_price = period_low_price * (1-threshold)
        # check if new low
        if current_price < period_low_price or last_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(exit_period)
            trading_logger.log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, current_price, round(period_low_price, 2)))
        # check if has long wick up
        elif pattern.check_bars_has_long_wick_up(bars, period=5, count=2):
            trading_logger.log(
                "<{}> candle chart has long wick up, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart has long wick up."
        # check if bar chart has volatility
        elif self.is_extended_market_hour() and not pattern.check_bars_volatility(bars):
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

        if not exit_trading:
            # additional check in subclass
            exit_trading, exit_note = self.check_exit_extra(ticker, bars)

        return (exit_trading, exit_note)

    def check_scale_in(self, ticker: TrackingTicker, bars: pd.DataFrame, position: dict) -> bool:
        return False

    def check_buy_dip(self, ticker: TrackingTicker, bars: pd.DataFrame, position: dict) -> bool:
        return False

    def check_stop_profit(self, ticker: TrackingTicker, position: dict) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate >= 1:
            exit_trading = True
            exit_note = "Home run at {}!".format(position['lastPrice'])
        return (exit_trading, exit_note)

    def check_stop_loss(self, ticker: TrackingTicker, position: dict) -> Tuple[bool, str]:
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        # check stop loss
        if last_price < ticker.get_stop_loss():
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        return (exit_trading, exit_note)

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        # current_price = current_candle['close']
        # use max( min( prev candle middle, buy price -2% ), buy price -5% )
        # return max(
        #     min(round((prev_candle['high'] + prev_candle['low']) / 2, 2),
        #         round(current_price * (1 - config.MIN_DAY_STOP_LOSS), 2)),
        #     round(current_price * (1 - config.MAX_DAY_STOP_LOSS), 2))
        stop_loss_1 = current_candle['low']
        stop_loss_2 = prev_candle['low']
        # if candle already up more than 10%
        if (current_candle['high'] - current_candle['low']) / current_candle['low'] > 0.1:
            stop_loss_1 = round(
                (current_candle['high'] + current_candle['low'] / 2), 2)
        if (prev_candle['high'] - prev_candle['low']) / prev_candle['low'] > 0.1:
            stop_loss_2 = round(
                (prev_candle['high'] + prev_candle['low']) / 2, 2)
        return min(stop_loss_1, stop_loss_2)

    def get_price_rate_of_change(self, bars: pd.DataFrame, period: int = 10) -> float:
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        period_price = period_bars.iloc[0]['close']
        current_price = bars.iloc[-1]['close']
        ROC = (current_price - period_price) / period_price * 100
        return ROC

    def update_exit_period(self, ticker: TrackingTicker, position: dict):
        pass

    def trade(self, ticker: TrackingTicker, m1_bars: pd.DataFrame = pd.DataFrame()):

        ticker_id = ticker.get_id()
        symbol = ticker.get_symbol()

        if ticker.has_pending_order():
            self.check_pending_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
            if ticker.is_tracking_timeout():
                trading_logger.log(
                    "Trading <{}> session timeout!".format(symbol))
                # stop ticker tracking
                self.trading_tracker.stop_tracking(ticker)
                return

            # fetch 1m bar charts
            if m1_bars.empty:
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.entry_period*self.time_scale+5))
            if m1_bars.empty:
                return
            bars = m1_bars
            if self.time_scale == 5:
                bars = utils.convert_5m_bars(m1_bars)

            # calculate and fill ema 9 data
            bars['ema9'] = bars['close'].ewm(span=9, adjust=False).mean()

            # check entry: current price above vwap, entry period minutes new high
            if self.check_entry(ticker, bars):
                # reset exit period
                ticker.set_exit_period(self.exit_period)
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
            # update exit period by profit loss rate
            self.update_exit_period(ticker, ticker_position)

            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            if profit_loss_rate > ticker.get_max_profit_loss_rate():
                ticker.set_max_profit_loss_rate(profit_loss_rate)

            # check stop profit, home run
            exit_trading, exit_note = self.check_stop_profit(
                ticker, ticker_position)

            if not exit_trading:
                # get 1m bar charts
                # check_bars_at_peak require 30 bars
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.exit_period*self.time_scale + 30))
                # check bars error
                if m1_bars.empty:
                    trading_logger.log(
                        "<{}> bars data error!".format(symbol))
                    exit_trading = True
                    exit_note = "Bars data error!"

            if not exit_trading:
                # convert bars
                bars = m1_bars
                if self.time_scale == 5:
                    bars = utils.convert_5m_bars(m1_bars)
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(
                    ticker, ticker_position)

            if not exit_trading:
                trading_logger.log("Checking exit for <{}>, price: ${}, unrealized P&L: {}%".format(
                    symbol, bars.iloc[-1]['close'], round(profit_loss_rate * 100, 2)))
                # check exit trade
                exit_trading, exit_note = self.check_exit(ticker, bars)

            # exit trading
            if exit_trading:
                trading_logger.log(
                    f"📈 Exit trading <{symbol}> P&L: {round(profit_loss_rate * 100, 2)}%")

                self.submit_sell_limit_order(ticker, note=exit_note)

            # check scale in position
            elif self.check_scale_in(ticker, bars, ticker_position):

                # update stop loss
                ticker.set_stop_loss(self.get_scale_stop_loss_price(bars))
                # submit buy limit order
                self.submit_buy_limit_order(ticker, note="Scale in.")

            # check buy the dip
            elif self.check_buy_dip(ticker, bars, ticker_position):

                # update stop loss
                ticker.set_stop_loss(self.get_dip_stop_loss_price(bars))
                # submit buy limit order
                self.submit_buy_limit_order(ticker, note="Buy dip.")

    def update(self):
        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        # find new ticker in top gainers
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
            # init tracking ticker
            ticker = TrackingTicker(symbol, ticker_id)
            # check if can trade with requirements, skip check top 1 gainer
            if not self.check_can_trade_ticker(ticker):
                # trading_logger.log(
                #     "Can not trade <{}>, skip...".format(symbol))
                continue
            # trading_logger.log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
                if self.is_extended_market_hour():
                    m1_bars = webullsdk.get_1m_bars(
                        ticker_id, count=(self.entry_period*self.time_scale+5))
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

    def final(self):

        # cancel all existing order
        webullsdk.cancel_all_orders()

        # track failed to sell positions
        self.track_rest_positions()


# Breakout day trading class, using ask price for entry

class DayTradingBreakoutAsk(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutAsk"

    def get_buy_price(self, ticker: TrackingTicker) -> Optional[float]:
        ticker_id = ticker.get_id()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        trading_logger.log_level2(quote)
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        return ask_price or last_price


# Breakout day trade, adjust exit period by profit & loss rate.

class DayTradingBreakoutDynExit(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutDynExit"

    def update_exit_period(self, ticker: TrackingTicker, position: dict):
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        current_exit_period = ticker.get_exit_period() or 1
        # if profit_loss_rate >= 0.9 and current_exit_period > 1:
        #     ticker.set_exit_period(1)
        # elif profit_loss_rate >= 0.7 and current_exit_period > 3:
        #     ticker.set_exit_period(3)
        if profit_loss_rate >= 0.5 and current_exit_period > 5:
            ticker.set_exit_period(5)
        elif profit_loss_rate >= 0.3 and current_exit_period > 7:
            ticker.set_exit_period(7)


# Breakout day trading class, will check earning stock during earning date

class DayTradingBreakoutEarnings(DayTradingBreakout):

    def __init__(self, paper: bool, trading_hour: TradingHourType):
        super().__init__(paper, trading_hour)
        self.earning_tickers: List[dict] = []

    def get_tag(self) -> str:
        return "DayTradingBreakoutEarnings"

    def get_setup(self) -> SetupType:
        if len(self.earning_tickers) == 0:
            if self.entry_period == 30:
                return SetupType.DAY_30_CANDLES_NEW_HIGH
            elif self.entry_period == 20:
                return SetupType.DAY_20_CANDLES_NEW_HIGH
            return SetupType.DAY_10_CANDLES_NEW_HIGH
        else:
            return SetupType.DAY_EARNINGS_GAP

    def check_trade(self, ticker: TrackingTicker, change_percentage: float):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        # check if can trade with requirements
        if not self.check_can_trade_ticker(ticker):
            return
        # check gap change
        if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
            if self.is_extended_market_hour():
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.entry_period+5))
                if m1_bars.empty:
                    return
                # use latest 2 candle
                latest_candle = m1_bars.iloc[-1]
                latest_candle2 = m1_bars.iloc[-2]
                # check if trasaction amount and volume meets requirement
                if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                    # start tracking ticker
                    self.trading_tracker.start_tracking(ticker)
                    trading_logger.log(
                        "Start trading <{}>...".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
            elif self.is_regular_market_hour():
                # start tracking ticker
                self.trading_tracker.start_tracking(ticker)
                trading_logger.log(
                    "Start trading <{}>...".format(symbol))
                # do trade
                self.trade(ticker)

    def begin(self):

        # check earning calendars
        today = date.today()
        if self.is_pre_market_hour() or self.is_regular_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="bmo")
        elif self.is_after_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="amc")
        # update earning_tickers
        for earning in earnings:
            symbol = earning.symbol
            ticker_id = str(webullsdk.get_ticker(symbol=symbol))
            self.earning_tickers.append({
                "symbol": symbol,
                "ticker_id": ticker_id,
            })
            trading_logger.log(
                "Add ticker <{}> to check earning gap!".format(symbol))

    def update(self):
        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        # no earning symbol found
        if len(self.earning_tickers) == 0:
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
                self.check_trade(ticker, change_percentage)
        else:
            for earning_ticker in self.earning_tickers:
                symbol = earning_ticker["symbol"]
                ticker_id = earning_ticker["ticker_id"]
                # check if ticker already tracking
                if self.trading_tracker.is_tracking(ticker_id):
                    continue
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    continue
                change_percentage = 0.0
                if self.is_extended_market_hour():
                    if 'pChRatio' in quote:
                        change_percentage = float(quote['pChRatio'])
                elif self.is_regular_market_hour():
                    if 'changeRatio' in quote:
                        change_percentage = float(quote['changeRatio'])
                ticker = TrackingTicker(symbol, ticker_id)
                self.check_trade(ticker, change_percentage)


# Breakout day trade, no entry if the price not break max of last high price.

class DayTradingBreakoutNewHigh(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutNewHigh"

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


# Breakout day trade, exit if trading period timeout.

class DayTradingBreakoutPeriod(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutPeriod"

    def check_exit_extra(self, ticker: TrackingTicker, bars: pd.DataFrame) -> Tuple[bool, str]:
        symbol = ticker.get_symbol()
        time_out = self.check_if_trade_period_timeout(ticker)
        exit_trading = False
        exit_note = None
        if time_out:
            trading_logger.log(
                "<{}> trading period timeout, exit!".format(symbol))
            exit_trading = True
            exit_note = "Trading period timeout."
        return (exit_trading, exit_note)

    def check_if_trade_period_timeout(self, ticker: TrackingTicker) -> bool:
        if (datetime.now() - ticker.get_last_buy_time()) >= timedelta(seconds=config.DAY_PERIOD_TIMEOUT_IN_SEC):
            return True
        return False


# Breakout day trade, find pre-market losers and aim for reversal.

class DayTradingBreakoutPreLosers(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutPreLosers"

    def begin(self):
        self.preloser_tickers = []
        # check pre-market losers
        if self.is_regular_market_hour():
            self.preloser_tickers = webullsdk.get_pre_market_losers(count=10)
            trading_logger.log("Add {} tickers to check loser reversal!".format(
                len(self.preloser_tickers)))

    def update(self):

        if self.is_pre_market_hour() or self.is_after_market_hour():
            # only trade in regular hour
            return

        # trading tickers
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            # do trade
            self.trade(ticker)

        for preloser_ticker in self.preloser_tickers:
            symbol = preloser_ticker["symbol"]
            ticker_id = str(preloser_ticker["ticker_id"])
            # check if ticker already tracking
            if self.trading_tracker.is_tracking(ticker_id):
                continue
            # found trading ticker
            ticker = TrackingTicker(symbol, ticker_id)
            self.trading_tracker.start_tracking(ticker)
            trading_logger.log("Start trading <{}>...".format(symbol))
            # do trade
            self.trade(ticker)


# Breakout day trading class, scale if reach add unit price

class DayTradingBreakoutScale(DayTradingBreakout):

    def get_tag(self) -> str:
        return "DayTradingBreakoutScale"

    def precheck_scale_in(self, ticker: TrackingTicker, position: dict) -> bool:
        last_buy_time = ticker.get_last_buy_time()
        target_units = 4
        units = 1
        position_obj = ticker.get_position_obj()
        if position_obj:
            target_units = position_obj.target_units
            units = position_obj.units
        # check if already reach target units
        if units >= target_units:
            return False
        # check if pass 5 minutes from initial buy or 1 minute from last buy
        trade_interval_sec = 60
        if units == 1:
            # give some time for trading to work out
            trade_interval_sec = 300
        if (datetime.now() - last_buy_time).seconds <= trade_interval_sec:
            return False
        # check if has 5% gain already
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate < 0.05:
            return False
        return True

    def check_scale_in(self, ticker: TrackingTicker, bars: pd.DataFrame, position: dict) -> bool:
        if not self.precheck_scale_in(ticker, position):
            return False
        symbol = ticker.get_symbol()
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        period_bars = bars.head(len(bars) - 1).tail(self.entry_period)
        period_high_price = 0
        for _, row in period_bars.iterrows():
            close_price = row['close']  # use close price
            if close_price > period_high_price:
                period_high_price = close_price

        # check if new high
        if current_price <= period_high_price:
            trading_logger.log(
                f"<{symbol}> price ${current_price} is not breakout high ${period_high_price}, no scale in!")
            return False

        if self.is_regular_market_hour() and not pattern.check_bars_updated(bars):
            trading_logger.log(
                "<{}> candle chart is not updated, stop scale in!".format(symbol))
            return False

        if self.is_regular_market_hour() and not pattern.check_bars_continue(bars, time_scale=self.time_scale):
            trading_logger.log(
                "<{}> candle chart is not continue, stop scale in!".format(symbol))
            return False

        if not pattern.check_bars_has_volume(bars):
            # has no enough volume
            trading_logger.log(
                "<{}> candle chart has no enough volume, no scale in!".format(symbol))
            return False

        if pattern.check_bars_has_long_wick_up(bars, period=self.entry_period):
            # has long wick up
            trading_logger.log(
                "<{}> candle chart has long wick up, no scale in!".format(symbol))
            return False

        if not (pattern.check_bars_has_largest_green_candle(bars) and pattern.check_bars_has_more_green_candle(bars)) and \
                not pattern.check_bars_has_most_green_candle(bars):
            # not most green candles and no largest green candle
            trading_logger.log(
                "<{}> candle chart has no most green candles or largest candle is red, no scale in!".format(symbol))
            return False

        if pattern.check_bars_has_bearish_candle(bars, period=5):
            # has bearish candle
            trading_logger.log(
                "<{}> candle chart has bearish candle, no scale in!".format(symbol))
            return False

        ROC = self.get_price_rate_of_change(bars, period=self.entry_period)
        if ROC <= config.DAY_SCALE_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            trading_logger.log(
                "<{}> candle chart price rate of change for {} period ({}) is weak, no scale in!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        trading_logger.log(
            "Scale in <{}> position, period breakout.".format(symbol))
        return True

    def get_scale_stop_loss_price(self, bars: pd.DataFrame) -> float:
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        stop_loss_1 = current_candle['low']
        stop_loss_2 = prev_candle['low']
        # if candle already up more than 10%
        if (current_candle['high'] - current_candle['low']) / current_candle['low'] > 0.1:
            stop_loss_1 = round(
                (current_candle['high'] + current_candle['low']) / 2, 2)
        if (prev_candle['high'] - prev_candle['low']) / prev_candle['low'] > 0.1:
            stop_loss_2 = round(
                (prev_candle['high'] + prev_candle['low']) / 2, 2)
        return min(stop_loss_1, stop_loss_2)

    def check_buy_dip(self, ticker: TrackingTicker, bars: pd.DataFrame, position: dict) -> bool:
        if not self.precheck_scale_in(ticker, position):
            return False
        symbol = ticker.get_symbol()
        last_candle = bars.iloc[-2]
        last_low = min(last_candle['open'], last_candle['close'])
        last_high = max(last_candle['open'], last_candle['close'])
        period_bars = bars.head(
            len(bars) - 2).tail(config.DAY_BUY_DIP_CANDLE_CHECK_COUNT)
        period_low_price = constants.MAX_SECURITY_PRICE
        for _, row in period_bars.iterrows():
            # use mid price, min(close, open)
            # low_price = min(row['close'], row['open'])
            low_price = row['close']
            if low_price < period_low_price:
                period_low_price = low_price

        # check if new low
        if last_low > period_low_price:
            return False

        current_candle = bars.iloc[-1]
        current_price = current_candle['close']

        if current_price <= last_high:
            # no first candle new high
            trading_logger.log(
                "<{}> candle not formed first candle new high, no buy dip!".format(symbol))
            return False

        # position size if buy
        pos_size = math.ceil(self.get_buy_order_limit(ticker) / current_price)
        if not pattern.check_bars_volume_with_pos_size(bars, pos_size, period=10):
            # volume not enough for my position size
            trading_logger.log(
                f"<{symbol}> candle chart volume is not enough for position size {pos_size}, no dip buy!")
            return False

        trading_logger.log(
            "Buy dip <{}> position, first candle new high.".format(symbol))
        return True

    def get_dip_stop_loss_price(self, bars: pd.DataFrame) -> float:
        prev_candle = bars.iloc[-2]
        return min(prev_candle['open'], prev_candle['close'])

    def check_stop_profit(self, ticker: TrackingTicker, position: dict) -> bool:
        exit_trading = False
        exit_note = None
        initial_cost = ticker.get_initial_cost()
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        last_price = float(position['lastPrice'])
        if initial_cost and initial_cost > 0:
            profit_loss_rate = (last_price - initial_cost) / initial_cost
        if profit_loss_rate >= 1:
            exit_trading = True
            exit_note = "Home run at {}!".format(last_price)
        return (exit_trading, exit_note)

    def update_exit_period(self, ticker: TrackingTicker, position: dict):
        initial_cost = ticker.get_initial_cost()
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        last_price = float(position['lastPrice'])
        # use initial cost price because of scale in
        if initial_cost and initial_cost > 0:
            profit_loss_rate = (last_price - initial_cost) / initial_cost
        current_exit_period = ticker.get_exit_period() or 1
        # if profit_loss_rate >= 0.9 and current_exit_period > 1:
        #     ticker.set_exit_period(1)
        # elif profit_loss_rate >= 0.7 and current_exit_period > 3:
        #     ticker.set_exit_period(3)
        if profit_loss_rate >= 0.5 and current_exit_period > 5:
            ticker.set_exit_period(5)
        elif profit_loss_rate >= 0.3 and current_exit_period > 7:
            ticker.set_exit_period(7)


# Breakout day trading class, scale if reach add unit price and max stop loss

class DayTradingBreakoutScaleStopLossMax(DayTradingBreakoutScale):

    def get_tag(self) -> str:
        return "DayTradingBreakoutScaleStopLossMax"

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        current_price = bars.iloc[-1]['close']
        # use max stop loss
        return round(current_price * (1 - config.MAX_DAY_STOP_LOSS), 2)


# Breakout day trading class, scale if reach add unit price and use average true range as stop loss

class DayTradingBreakoutScaleStopLossATR(DayTradingBreakoutScale):

    def get_tag(self) -> str:
        return "DayTradingBreakoutScaleStopLossATR"

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:

        current_price = bars.iloc[-1]['close']

        N = utils.get_day_avg_true_range(bars)
        atr_stop_loss_price = round(current_price - N, 2)

        prev_candle = bars.iloc[-2]
        # use max( min( prev candle middle, buy price -2% ), buy price -5% )
        stop_loss_price = max(
            min(round((prev_candle['high'] + prev_candle['low']) / 2, 2),
                round(current_price * (1 - config.MIN_DAY_STOP_LOSS), 2)),
            round(current_price * (1 - config.MAX_DAY_STOP_LOSS), 2))

        return max(atr_stop_loss_price, stop_loss_price)

    def get_scale_stop_loss_price(self, bars: pd.DataFrame) -> float:
        # current_price = bars.iloc[-1]['close']
        # N = utils.get_day_avg_true_range(bars)
        # return round(current_price - N, 2)
        return 0.0


# Breakout day trading class, scale if reach add unit price and use period high as ROC check

class DayTradingBreakoutScalePeriodROC(DayTradingBreakoutScale):

    def get_tag(self) -> str:
        return "DayTradingBreakoutScalePeriodROC"

    def get_price_rate_of_change(self, bars: pd.DataFrame, period: int = 10) -> float:
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(int(period / 2))
        period_high_price = 0.1
        for _, row in period_bars.iterrows():
            price = row["close"]
            if price > period_high_price:
                period_high_price = price
        prev_price = bars.iloc[-2]['close']
        # if prev price is highest, no ROC required
        if prev_price > period_high_price:
            return config.DAY_PRICE_RATE_OF_CHANGE + 1
        current_price = bars.iloc[-1]['close']
        ROC = (current_price - period_high_price) / period_high_price * 100
        return ROC
