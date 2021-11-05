from typing import List
import pandas as pd
from datetime import datetime
from common import utils, config
from webull_trader.models import SwingHistoricalDailyBar


def _check_trading_time_match(time: datetime) -> bool:
    """
    check if given time is same as current market hour
    """
    if utils.is_regular_market_hour_now() and not utils.is_regular_market_time(time):
        return False
    if utils.is_pre_market_hour_now() and not utils.is_pre_market_time(time):
        return False
    if utils.is_after_market_hour_now() and not utils.is_after_market_time(time):
        return False
    return True


def _get_avg_confirm_volume() -> float:
    if utils.is_paper_trading():
        if utils.is_regular_market_hour_now():
            return config.PAPER_AVG_CONFIRM_VOLUME
        return config.PAPER_EXTENDED_AVG_CONFIRM_VOLUME
    else:
        if utils.is_regular_market_hour_now():
            return config.AVG_CONFIRM_VOLUME
        return config.EXTENDED_AVG_CONFIRM_VOLUME


def _get_avg_confirm_amount() -> float:
    if utils.is_regular_market_hour_now():
        return config.AVG_CONFIRM_AMOUNT
    return config.EXTENDED_AVG_CONFIRM_AMOUNT


def _get_min_rel_volume_ratio() -> float:
    if utils.is_regular_market_hour_now():
        return config.DAY_MIN_RELATIVE_VOLUME
    return config.DAY_EXTENDED_MIN_RELATIVE_VOLUME


def _get_vol_for_pos_size(size: float) -> float:
    if utils.is_regular_market_hour_now():
        return config.DAY_VOLUME_POS_SIZE_RATIO * size
    return config.DAY_EXTENDED_VOLUME_POS_SIZE_RATIO * size


def check_bars_continue(bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
    """
    check if candle bar is continue of time scale minutes
    """
    period = min(len(bars) - 1, period)
    last_minute = -1
    is_continue = True
    period_bars = bars.tail(period)
    for index, _ in period_bars.iterrows():
        time = index.to_pydatetime()
        if not _check_trading_time_match(time):
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


def check_bars_updated(bars: pd.DataFrame, time_scale: int = 1) -> bool:
    """
    check if have valid latest chart data, delay no more than 1 minute
    """
    if len(bars) < 1:
        return False
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    current_timestamp = int(datetime.timestamp(datetime.now()))
    if current_timestamp - latest_timestamp <= 60 * time_scale:
        return True
    return False


def check_bars_current_low_less_than_prev_low(bars: pd.DataFrame) -> bool:
    """
    check if current low price less than prev low price
    """
    if len(bars) < 2:
        return False
    current_low = bars.iloc[-1]['low']
    prev_low = bars.iloc[-2]['low']
    if current_low < prev_low:
        return True
    return False


def check_bars_price_fixed(bars: pd.DataFrame) -> bool:
    """
    check if prev chart candlestick price is fixed
    """
    if len(bars) < 5:
        return False
    prev_close2 = bars.iloc[-2]['close']
    prev_close3 = bars.iloc[-3]['close']
    prev_close4 = bars.iloc[-4]['close']

    prev_open2 = bars.iloc[-2]['open']
    prev_open3 = bars.iloc[-3]['open']
    prev_open4 = bars.iloc[-4]['open']

    if prev_close2 == prev_close3 and prev_close3 == prev_close4 and \
            prev_open2 == prev_open3 and prev_open3 == prev_open4:
        return True
    return False


def check_bars_has_volume(bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
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
            if not _check_trading_time_match(time):
                continue
            volume = row["volume"]
            total_volume += volume
        avg_volume = total_volume / float(period)
        confirm_volume = _get_avg_confirm_volume() * time_scale
        if avg_volume >= confirm_volume:
            has_volume = True
            break
    return has_volume


def check_bars_has_volume2(bars: pd.DataFrame) -> bool:
    """
    check if bar chart has enough volume for 2 bars
    """
    if len(bars) <= 3:
        return False
    confirm_volume = _get_avg_confirm_volume()
    current_bar = bars.iloc[-1]
    prev_bar2 = bars.iloc[-2]
    prev_bar3 = bars.iloc[-3]
    if max(current_bar["volume"], prev_bar2["volume"], prev_bar3["volume"]) >= confirm_volume:
        return True
    return False


def check_bars_has_amount(bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
    """
    check if bar chart has enough amount
    """
    # make sure not use the last candle
    period = min(len(bars) - 1, period)
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    total_amount = 0.0
    for index, row in period_bars.iterrows():
        time = index.to_pydatetime()
        if not _check_trading_time_match(time):
            continue
        volume = row["volume"]
        price = row["close"]
        total_amount += (volume * price)

    avg_amount = total_amount / float(period)
    confirm_amount = _get_avg_confirm_amount() * time_scale

    return avg_amount >= confirm_amount


def check_bars_volume_with_pos_size(bars: pd.DataFrame, size: int, period: int = 10) -> bool:
    # make sure not use the last candle
    period = min(len(bars) - 1, period)
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    volume_is_enough = True
    target_volume = _get_vol_for_pos_size(size)
    for index, row in period_bars.iterrows():
        time = index.to_pydatetime()
        if not _check_trading_time_match(time):
            continue
        volume = row["volume"]
        if volume < target_volume:
            volume_is_enough = False
            break
    return volume_is_enough


def check_bars_amount_grinding(bars: pd.DataFrame, period: int = 10) -> bool:
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
        if not _check_trading_time_match(time):
            continue
        volume = row["volume"]
        price = row["close"]
        current_amount = volume * price
        if current_amount < prev_amount:
            amount_grinding = False
            break
        prev_amount = current_amount

    return amount_grinding


def check_bars_has_long_wick_up(bars: pd.DataFrame, period: int = 5, count: int = 1) -> bool:
    """
    check if bar chart has long wick up
    """
    long_wick_up_count = 0
    period = min(len(bars) - 1, period)
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    # calculate average candle size
    total_candle_size = 0.0
    for _, row in period_bars.iterrows():
        high = row["high"]
        low = row["low"]
        candle_size = high - low
        total_candle_size += candle_size
    avg_candle_size = 0.0
    if len(period_bars) > 0:
        avg_candle_size = total_candle_size / len(period_bars)
    prev_row = pd.Series()
    prev_candle_size = 0.0
    for _, row in period_bars.iterrows():
        mid = max(row["close"], row["open"])
        high = row["high"]
        low = row["low"]
        # # make sure the candle is red
        # if row["close"] > row["open"]:
        #     continue
        # make sure long wick body is larger than average candle size
        if (high - low) < avg_candle_size * config.LONG_WICK_AVG_CANDLE_RATIO:
            continue
        # marke sure no less than prev bar
        if not prev_row.empty:
            prev_candle_size = prev_row["high"] - prev_row["low"]
        if (high - low) < prev_candle_size * config.LONG_WICK_PREV_CANDLE_RATIO:
            continue
        # make sure wick tail is larger than body
        if (high - mid) <= abs(row["close"] - row["open"]):
            continue
        if (mid - low) > 0 and (high - mid) / (mid - low) >= config.LONG_WICK_UP_RATIO:
            long_wick_up_count += 1
        elif (mid - low) == 0 and (high - mid) > 0:
            long_wick_up_count += 1
        prev_row = row
    return long_wick_up_count >= count


def check_bars_has_bearish_candle(bars: pd.DataFrame, period: int = 5, count: int = 1) -> bool:
    """
    check if bar chart has bearish candle
    """
    bearish_candle_count = 0
    period = min(len(bars) - 1, period)
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    # calculate average candle size
    total_candle_size = 0.0
    for _, row in period_bars.iterrows():
        candle_size = abs(row["close"] - row["open"])
        total_candle_size += candle_size
    avg_candle_size = 0.0
    if len(period_bars) > 0:
        avg_candle_size = total_candle_size / len(period_bars)
    for _, row in period_bars.iterrows():
        if row["open"] > row["close"]:
            bearish_candle_size = row["open"] - row["close"]
            # make sure bearish body is larger than average candle size
            if bearish_candle_size < avg_candle_size * config.BEARISH_AVG_CANDLE_RATIO:
                continue
            bearish_candle_count += 1
    return bearish_candle_count >= count


def check_bars_at_peak(bars: pd.DataFrame, long_period: int = 10, short_period: int = 3) -> bool:
    """
    check if bar chart is at peak
    """
    if len(bars) < long_period * 2:
        return False
    prev_bar2 = bars.iloc[-2]
    # prev_bar2 should be red
    if prev_bar2['close'] > prev_bar2['open']:
        return False
    prev_bar3 = bars.iloc[-3]
    # prev_bar3 should be green
    if prev_bar3['close'] < prev_bar3['open']:
        return False
    # prev_bar3 price should be highest
    for _, row in bars.iterrows():
        if prev_bar3['close'] < row['close']:
            return False
    # prev_bar3 should has enough up percentage (5%)
    if (prev_bar3['close'] - prev_bar3['open']) / prev_bar3['open'] < 0.05:
        return False
    # prev_bar3 vol should > prev_bar2 vol
    # if prev_bar3['volume'] < prev_bar2['volume']:
    #     return False
    # prev_bar3 vol should > avg long_period vol
    total_vol = 0
    for i in range(0, long_period):
        total_vol += bars.iloc[-4 - i]['volume']
    avg_vol = total_vol / long_period
    if prev_bar3['volume'] < avg_vol:
        return False
    # prev_bar3 vol should > each short_period vol
    for i in range(0, short_period):
        short_vol = bars.iloc[-4 - i]['volume']
        if prev_bar3['volume'] < short_vol:
            return False
    # long period vol should > pre long period vol * 4
    prev_total_vol = 0
    for i in range(0, long_period):
        prev_total_vol += bars.iloc[-4 - long_period - i]['volume']
    prev_avg_vol = prev_total_vol / long_period
    if avg_vol < prev_avg_vol * 4:
        return False
    # at peak
    return True


def check_bars_reversal(bars: pd.DataFrame, period: int = 5) -> bool:
    """
    check if bar chart will reversal
    http://live2.webull-trader.quanturtle.net/day-analytics/2021-10-14/LMFA
    http://live2.webull-trader.quanturtle.net/day-analytics/2021-10-15/NXTD
    """
    if len(bars) < period + 1:
        return False
    prev_bar2 = bars.iloc[-2]
    # prev_bar2 should be red
    if prev_bar2['close'] > prev_bar2['open']:
        return False
    # prev_bar2 up wick should > down wick or body
    prev_bar2_high = prev_bar2['high']
    prev_bar2_low = prev_bar2['low']
    prev_bar2_up = max(prev_bar2['open'], prev_bar2['close'])
    prev_bar2_down = min(prev_bar2['open'], prev_bar2['close'])
    prev_bar2_up_wick = prev_bar2_high - prev_bar2_up
    prev_bar2_down_wick = prev_bar2_down - prev_bar2_low
    prev_bar2_body = prev_bar2_up - prev_bar2_down
    if prev_bar2_up_wick < max(prev_bar2_down_wick, prev_bar2_body):
        return False
    # prev_bar2_mid = max(prev_bar2['open'], prev_bar2['close'])
    # prev_bar2_body = abs(prev_bar2['close'] - prev_bar2['open'])
    # prev_bar2_up_wick = (prev_bar2['high'] - prev_bar2_mid)
    # prev_bar2_down_wick = (prev_bar2['high'] - prev_bar2_mid)
    # # prev_bar2 should has long up tail, up wick > 2 * down wick and up wick > body
    # if prev_bar2_up_wick < 2 * prev_bar2_down_wick or prev_bar2_up_wick < prev_bar2_body:
    #     return False
    prev_bar3 = bars.iloc[-3]
    # prev_bar3 should be green
    if prev_bar3['close'] < prev_bar3['open']:
        return False
    # prev_bar2 open should > prev_bar3 close
    if prev_bar2['open'] < prev_bar3['close']:
        return False
    current_bar = bars.iloc[-1]
    # current_bar price should < prev_bar3 low
    if current_bar['close'] > prev_bar3['low']:
        return False
    # reversal bar should period high
    period = min(len(bars) - 2, period)
    period_bars = bars.tail(period + 2)
    period_bars = period_bars.head(period)
    period_high_price = 0.0
    for _, row in period_bars.iterrows():
        if row['high'] > period_high_price:
            period_high_price = row['high']
    if prev_bar2['high'] < period_high_price:
        return False
    # reversal
    return True


def check_bars_rel_volume(bars: pd.DataFrame) -> bool:
    """
    check if bar chart relative volume
    """
    if len(bars) < 8:
        return False
    # check relative volume over 3
    last_candle2 = bars.iloc[-2]
    last_candle3 = bars.iloc[-3]
    last_candle4 = bars.iloc[-4]
    last_candle5 = bars.iloc[-5]
    last_candle6 = bars.iloc[-6]
    last_candle7 = bars.iloc[-7]

    min_relvol = _get_min_rel_volume_ratio()

    if (last_candle2["volume"] + last_candle3["volume"]) / (last_candle4["volume"] + last_candle5["volume"]) > min_relvol or \
        (last_candle2["volume"] + last_candle3["volume"] + last_candle4["volume"]) / (last_candle5["volume"] + last_candle6["volume"] + last_candle7["volume"]) > min_relvol or \
        last_candle2["volume"] / last_candle3["volume"] > min_relvol or last_candle3["volume"] / last_candle4["volume"] > min_relvol or \
        last_candle4["volume"] / last_candle5["volume"] > min_relvol or last_candle5["volume"] / last_candle6["volume"] > min_relvol or \
            last_candle6["volume"] / last_candle7["volume"] > min_relvol:
        # relative volume ok
        return True
    return False


def check_bars_all_green(bars: pd.DataFrame, period: int = 5) -> bool:
    """
    check if has bar's candle all green
    """
    period = min(len(bars) - 1, period)
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    all_candle_green = True
    for _, row in period_bars.iterrows():
        if row['open'] > row['close']:
            all_candle_green = False
    return all_candle_green


def check_bars_volatility(bars: pd.DataFrame, period: int = 5) -> bool:
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
        if (utils.is_pre_market_hour_now() and utils.is_pre_market_time(time)) or (utils.is_after_market_hour_now() and utils.is_after_market_time(time)) or \
                (utils.is_regular_market_hour_now() and utils.is_regular_market_time(time)):
            valid_candle_count += 1
        # check for pre market hour except for first 15 minutes
        if utils.is_pre_market_hour_now() and not utils.is_pre_market_hour_15m() and utils.is_pre_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # check for after market hour only
        if utils.is_after_market_hour_now() and not utils.is_after_market_hour_15m() and utils.is_after_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # check for regular market hour only
        if utils.is_regular_market_hour_now() and not utils.is_regular_market_hour_15m() and utils.is_regular_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # add price value set
        price_set.add(row['open'])
        price_set.add(row['high'])
        price_set.add(row['low'])
        price_set.add(row['close'])
    if valid_candle_count == len(period_bars):
        # price not like open: 7.35, high: 7.35, low: 7.35, close: 7.35
        if flat_count >= 3:
            return False
        # price set only in a few values
        if len(price_set) <= 2:
            return False
    return True


def check_bars_has_largest_green_candle(bars: pd.DataFrame, period: int = 10) -> bool:
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
        if not _check_trading_time_match(time):
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


def check_bars_has_most_green_candle(bars: pd.DataFrame, period: int = 10) -> bool:
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
        if not _check_trading_time_match(time):
            continue
        # green candle
        if row['close'] >= row['open']:
            green_candle_count += 1
        total_candle_count += 1
    # make sure total is not zero
    total_candle_count = max(1, total_candle_count)
    return float(green_candle_count) / float(total_candle_count) >= config.CHART_MOST_GREEN_CANDLES_THRESHOLD


def check_bars_has_more_green_candle(bars: pd.DataFrame, period: int = 10) -> bool:
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
        if not _check_trading_time_match(time):
            continue
        # green candle
        if row['close'] >= row['open']:
            green_candle_count += 1
        total_candle_count += 1
    # make sure total is not zero
    total_candle_count = max(1, total_candle_count)
    return float(green_candle_count) / float(total_candle_count) >= config.CHART_MORE_GREEN_CANDLES_THRESHOLD


# daily candle pattern

def check_daily_bars_volume_grinding(bars: List[SwingHistoricalDailyBar], period: int = 10) -> bool:
    """
    check if daily bar chart volume is grinding
    """
    period_bars = bars[-period:]
    prev_vol = 0
    vol_grinding = True
    for period_bar in period_bars:
        volume = period_bar.volume
        if volume < prev_vol:
            vol_grinding = False
            break
        prev_vol = volume
    return vol_grinding


def check_daily_bars_rel_volume(bars: List[SwingHistoricalDailyBar]) -> bool:
    """
    check if daily bar chart relative volume
    """
    # check relative volume over 2
    for i in range(1, 5):
        curent_period_bars = bars[-i:]
        current_period_vol = 0
        for bar in curent_period_bars:
            current_period_vol += bar.volume
        prev_period_bars = bars[-i*2:-i]
        prev_period_vol = 0
        for bar in prev_period_bars:
            prev_period_vol += bar.volume
        if current_period_vol / prev_period_vol > config.SWING_MIN_RELATIVE_VOLUME:
            # relative volume ok
            return True
    return False
