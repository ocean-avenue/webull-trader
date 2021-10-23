import pandas as pd
import numpy as np
from datetime import datetime


def _open_resampler(series):
    if series.size > 0:
        return series[0]
    return 0


def _close_resampler(series):
    if series.size > 0:
        return series[-1]
    return 0


def _high_resampler(series):
    if series.size > 0:
        return np.max(series)
    return 0


def _low_resampler(series):
    if series.size > 0:
        return np.min(series)
    return 0


def _volume_resampler(series):
    if series.size > 0:
        return np.sum(series)
    return 0


def _vwap_resampler(series):
    if series.size > 0:
        return series[-1]
    return 0


def convert_2m_bars(bars):
    if not bars.empty:
        bars_2m = pd.DataFrame()
        bars_2m_open = bars['open'].resample(
            '2T', label="right", closed="right").apply(_open_resampler)
        bars_2m_close = bars['close'].resample(
            '2T', label="right", closed="right").apply(_close_resampler)
        bars_2m_high = bars['high'].resample(
            '2T', label="right", closed="right").apply(_high_resampler)
        bars_2m_low = bars['low'].resample(
            '2T', label="right", closed="right").apply(_low_resampler)
        bars_2m_volume = bars['volume'].resample(
            '2T', label="right", closed="right").apply(_volume_resampler)
        bars_2m_vwap = bars['vwap'].resample(
            '2T', label="right", closed="right").apply(_vwap_resampler)
        bars_2m['open'] = bars_2m_open
        bars_2m['close'] = bars_2m_close
        bars_2m['high'] = bars_2m_high
        bars_2m['low'] = bars_2m_low
        bars_2m['volume'] = bars_2m_volume
        bars_2m['vwap'] = bars_2m_vwap
        # filter zero row
        return bars_2m.loc[(bars_2m != 0).all(axis=1), :]
    return pd.DataFrame()


def convert_5m_bars(bars):
    if not bars.empty:
        bars_5m = pd.DataFrame()
        bars_5m_open = bars['open'].resample(
            '5T', label="right", closed="right").apply(_open_resampler)
        bars_5m_close = bars['close'].resample(
            '5T', label="right", closed="right").apply(_close_resampler)
        bars_5m_high = bars['high'].resample(
            '5T', label="right", closed="right").apply(_high_resampler)
        bars_5m_low = bars['low'].resample(
            '5T', label="right", closed="right").apply(_low_resampler)
        bars_5m_volume = bars['volume'].resample(
            '5T', label="right", closed="right").apply(_volume_resampler)
        bars_5m_vwap = bars['vwap'].resample(
            '5T', label="right", closed="right").apply(_vwap_resampler)
        bars_5m['open'] = bars_5m_open
        bars_5m['close'] = bars_5m_close
        bars_5m['high'] = bars_5m_high
        bars_5m['low'] = bars_5m_low
        bars_5m['volume'] = bars_5m_volume
        bars_5m['vwap'] = bars_5m_vwap
        # filter zero row
        return bars_5m.loc[(bars_5m != 0).all(axis=1), :]
    return pd.DataFrame()


def check_bars_updated(bars: pd.DataFrame, time_scale: int = 1):
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
