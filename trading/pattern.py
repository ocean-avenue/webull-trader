import pandas as pd
from datetime import datetime
from common import utils, config


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
    return config.EXTENDED_DAY_MIN_RELATIVE_VOLUME


def check_bars_continue(bars: pd.DataFrame, time_scale: int = 1, period: int = 10) -> bool:
    """
    check if candle bar is continue of time scale minutes
    """
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
    current_low = bars.iloc[-1]['low']
    prev_low = bars.iloc[-2]['low']
    if current_low < prev_low:
        return True
    return False


def check_bars_price_fixed(bars: pd.DataFrame) -> bool:
    """
    check if prev chart candlestick price is fixed
    """
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
    period_bars = bars.tail(period + 1)
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

    return avg_volume >= confirm_volume


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


def check_bars_has_long_wick_up(bars, period=5, count=1):
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
