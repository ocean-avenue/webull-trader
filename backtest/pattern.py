from datetime import datetime
from django.utils import timezone
import pandas as pd
from common import utils
from backtest import config


class BacktestPattern:

    def __init__(self):
        self.trading_time = None

    def set_trading_time(self, time: datetime):
        self.trading_time = time.astimezone(timezone.get_current_timezone())

    def _check_trading_time_match(self, time: datetime) -> bool:
        """
        check if given time is same as current market hour
        """
        if utils.is_regular_market_time(self.trading_time) and not utils.is_regular_market_time(time):
            return False
        if utils.is_pre_market_time(self.trading_time) and not utils.is_pre_market_time(time):
            return False
        if utils.is_after_market_time(self.trading_time) and not utils.is_after_market_time(time):
            return False
        return True

    def _get_vol_for_pos_size(self, size: float) -> float:
        if utils.is_regular_market_hour_now():
            return config.DAY_VOLUME_POS_SIZE_RATIO * size
        return config.DAY_EXTENDED_VOLUME_POS_SIZE_RATIO * size

    def _get_avg_confirm_volume(self) -> float:
        if utils.is_regular_market_hour_now():
            return config.AVG_CONFIRM_VOLUME
        return config.EXTENDED_AVG_CONFIRM_VOLUME

    def check_bars_updated(self, bars: pd.DataFrame, time_scale: int = 1) -> bool:
        """
        check if have valid latest chart data, delay no more than 1 minute
        """
        if len(bars) < 1:
            return False
        latest_index = bars.index[-1]
        latest_timestamp = int(datetime.timestamp(
            latest_index.to_pydatetime()))
        current_timestamp = int(datetime.timestamp(self.trading_time))
        if current_timestamp - latest_timestamp <= 60 * time_scale:
            return True
        return False

    def check_bars_continue(self, bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
        """
        check if candle bar is continue of time scale minutes
        """
        period = min(len(bars) - 1, period)
        last_minute = -1
        is_continue = True
        period_bars = bars.tail(period)
        for index, _ in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            if last_minute == -1:
                last_minute = time.minute
                continue
            current_minute = time.minute
            if time.minute == 0:
                current_minute = 60
            if current_minute - last_minute != time_scale:
                is_continue = False
                break
            last_minute = time.minute
        return is_continue

    def check_bars_amount_grinding(self, bars: pd.DataFrame, period: int = 10) -> bool:
        """
        check if bar chart amount is grinding
        """
        # make sure not use the last candle
        period = min(len(bars) - 1, period)
        amount_grinding = True
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        prev_amount = 0
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            volume = row["volume"]
            price = row["close"]
            current_amount = volume * price
            if current_amount < prev_amount:
                amount_grinding = False
                break
            prev_amount = current_amount

        return amount_grinding

    def check_bars_has_volume(self, bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
        """
        check if bar chart has enough volume
        """
        if len(bars) < period + 1:
            return False
        has_volume = False
        # check current, pre or pre, prepre two candles
        for i in range(0, 2):
            period_bars = bars.tail(period + i)
            period_bars = period_bars.head(period)
            total_volume = 0.0
            for index, row in period_bars.iterrows():
                time = index.to_pydatetime()
                if not self._check_trading_time_match(time):
                    continue
                volume = row["volume"]
                total_volume += volume
            avg_volume = total_volume / float(period)
            confirm_volume = self._get_avg_confirm_volume() * time_scale
            if avg_volume >= confirm_volume:
                has_volume = True
                break
        return has_volume

    def check_bars_volatility(self, bars: pd.DataFrame, period: int = 5) -> bool:
        """
        check if has bar's ohlc has different price
        """
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        flat_count = 0
        valid_candle_count = 0
        price_set = set()
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            # check valid candle
            if (utils.is_pre_market_time(self.trading_time) and utils.is_pre_market_time(time)) or (utils.is_after_market_time(self.trading_time) and utils.is_after_market_time(time)) or \
                    (utils.is_regular_market_time(self.trading_time) and utils.is_regular_market_time(time)):
                valid_candle_count += 1
            # check for pre market hour except for first 15 minutes
            if utils.is_pre_market_time(self.trading_time) and utils.is_pre_market_time(time):
                if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                    flat_count += 1
            # check for after market hour only
            if utils.is_after_market_time(self.trading_time) and utils.is_after_market_time(time):
                if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                    flat_count += 1
            # check for regular market hour only
            if utils.is_regular_market_time(self.trading_time) and utils.is_regular_market_time(time):
                if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                    flat_count += 1
            # add price value set
            price_set.add(row['open'])
            price_set.add(row['high'])
            price_set.add(row['low'])
            price_set.add(row['close'])
        if valid_candle_count == len(bars):
            # price not like open: 7.35, high: 7.35, low: 7.35, close: 7.35
            if flat_count >= 3:
                return False
            # price set only in a few values
            if len(price_set) <= 2:
                return False
        return True

    def check_bars_has_largest_green_candle(self, bars: pd.DataFrame, period: int = 10) -> bool:
        """
        check if candle chart in period's largest candle is green
        """
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        max_green_candle_size = 0.0
        max_red_candle_size = 0.0
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            # red candle
            if row['open'] > row['close']:
                red_candle_size = row['open'] - row['close']
                if red_candle_size > max_red_candle_size:
                    max_red_candle_size = red_candle_size
            # green candle
            if row['close'] > row['open']:
                green_candle_size = row['close'] - row['open']
                if green_candle_size > max_green_candle_size:
                    max_green_candle_size = green_candle_size
        return max_green_candle_size > max_red_candle_size

    def check_bars_has_more_green_candle(self, bars: pd.DataFrame, period: int = 10) -> bool:
        """
        check if candle chart in period are more green candles
        """
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        green_candle_count = 0
        total_candle_count = 0
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            # green candle
            if row['close'] >= row['open']:
                green_candle_count += 1
            total_candle_count += 1
        # make sure total is not zero
        total_candle_count = max(1, total_candle_count)
        return float(green_candle_count) / float(total_candle_count) >= config.CHART_MORE_GREEN_CANDLES_THRESHOLD

    def check_bars_has_most_green_candle(self, bars: pd.DataFrame, period: int = 10) -> bool:
        """
        check if candle chart in period are most green candles
        """
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        green_candle_count = 0
        total_candle_count = 0
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            # green candle
            if row['close'] >= row['open']:
                green_candle_count += 1
            total_candle_count += 1
        # make sure total is not zero
        total_candle_count = max(1, total_candle_count)
        return float(green_candle_count) / float(total_candle_count) >= config.CHART_MOST_GREEN_CANDLES_THRESHOLD

    def check_bars_volume_with_pos_size(self, bars: pd.DataFrame, size: int, period: int = 10) -> bool:
        # make sure not use the last candle
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        volume_is_enough = True
        target_volume = self._get_vol_for_pos_size(size)
        for index, row in period_bars.iterrows():
            time = index.to_pydatetime()
            if not self._check_trading_time_match(time):
                continue
            volume = row["volume"]
            if volume < target_volume:
                volume_is_enough = False
                break
        return volume_is_enough
