from os import sync
import pandas as pd
import numpy as np
import pytz
from django.conf import settings
from datetime import datetime
from old_ross import enums
from old_ross.models import WebullOrder, WebullOrderNote, HistoricalMinuteBar, HistoricalDailyBar


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_market_hour():
    return is_regular_market_hour() or is_extended_market_hour()


def is_extended_market_hour():
    return is_pre_market_hour() or is_after_market_hour()


def is_pre_market_hour():
    """
    NY pre market hour from 04:00 to 09:30
    """
    now = datetime.now()
    if now.hour < 4 or now.hour > 9:
        return False
    # stop pre market earlier for 5 minutes
    if now.hour == 9 and now.minute >= 25:
        return False
    # wait 3 min for webull get pre market data ready
    if now.hour == 4 and now.minute < 3:
        return False
    return True


def is_after_market_hour():
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    # wait 3 min for webull get after market data ready
    if now.hour == 16 and now.minute < 3:
        return False
    # stop after market earlier for 5 minutes
    if now.hour == 19 and now.minute >= 55:
        return False
    return True


def is_regular_market_hour():
    """
    NY regular market hour from 09:30 to 16:00
    """
    now = datetime.now()
    if now.hour < 9 or now.hour >= 16:
        return False
    # wait 3 min for webull get regular market data ready
    if now.hour == 9 and now.minute < 33:
        return False
    # stop regular market earlier for 5 minutes
    if now.hour == 15 and now.minute >= 55:
        return False
    return True


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
        return np.average(series)
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


def check_since_last_sell_too_short(last_sell_time, bars):
    """
    check if last sell candle is same as currently candle
    """
    if last_sell_time == None:
        return False
    last_sell_timestamp = int(datetime.timestamp(last_sell_time))
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    last_sell_minutes = int(last_sell_timestamp / 60)
    latest_minutes = int(latest_timestamp / 60)
    if latest_minutes == last_sell_minutes:
        return True
    return False


def check_bars_updated(bars):
    """
    check if have valid latest chart data, delay no more than 1 minute
    """
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    current_timestamp = int(datetime.timestamp(datetime.now()))
    if current_timestamp - latest_timestamp <= 60:
        return True
    return False


def check_bars_current_low_less_than_prev_low(bars):
    """
    check if current low price less than prev low price
    """
    if not bars.empty:
        current_low = bars.iloc[-1]['low']
        prev_low = bars.iloc[-2]['low']
        if current_low < prev_low:
            return True
    return False


def check_bars_price_fixed(bars):
    """
    check if prev chart candlestick price is fixed
    """
    if not bars.empty:
        prev_close2 = bars.iloc[-2]['close']
        prev_close3 = bars.iloc[-3]['close']
        prev_close4 = bars.iloc[-4]['close']
        if prev_close2 == prev_close3 and prev_close3 == prev_close4:
            return True
    return False


def calculate_charts_ema9(charts):
    """
    https://school.stockcharts.com/doku.php?id=technical_indicators:moving_averages
    """
    multiplier = 2 / (9 + 1)
    charts_length = len(charts)
    for i in range(0, charts_length):
        candle = charts[charts_length - i - 1]
        if i < 8:
            candle['ema9'] = 0
        elif i == 8:
            # use sma for initial ema
            sum = 0.0
            for j in (0, 8):
                c = charts[charts_length - j - 1]
                sum += c['close']
            candle['ema9'] = round(sum / 9, 2)
        else:
            prev_candle = charts[charts_length - i]
            candle['ema9'] = round(
                (candle['close'] - prev_candle['ema9']) * multiplier + prev_candle['ema9'], 2)
    return charts


def get_order_action_enum(action_str):
    action = enums.ActionType.BUY
    if action_str == "SELL":
        action = enums.ActionType.SELL
    return action


def get_order_status_enum(status_str):
    status = enums.StatusType.FILLED
    if status_str == "Cancelled":
        status = enums.StatusType.CANCELLED
    elif status_str == "Working":
        status = enums.StatusType.WORKING
    elif status_str == "Pending":
        status = enums.StatusType.PENDING
    elif status_str == "Failed":
        status = enums.StatusType.FAILED
    return status


def get_time_in_force_enum(time_in_force_str):
    time_in_force = enums.TimeInForceType.GTC
    if time_in_force_str == "DAY":
        time_in_force = enums.TimeInForceType.DAY
    elif time_in_force_str == "IOC":
        time_in_force = enums.TimeInForceType.IOC
    return time_in_force


def save_webull_order(order_data, paper=True):
    order_id = str(order_data['orderId'])
    order = WebullOrder.objects.filter(order_id=order_id).first()
    symbol = order_data['ticker']['symbol']
    print("[{}] Importing Order <{}> {} ({})...".format(
        get_now(), symbol, order_id, order_data['placedTime']))
    if order:
        print("[{}] Order <{}> {} ({}) already existed!".format(
            get_now(), symbol, order_id, order_data['placedTime']))
    else:
        ticker_id = str(order_data['ticker']['tickerId'])
        action = get_order_action_enum(order_data['action'])
        status = get_order_status_enum(order_data['status'])
        total_quantity = int(order_data['totalQuantity'])
        filled_quantity = int(order_data['filledQuantity'])
        price = float(order_data['lmtPrice'])
        avg_price = 0
        if 'avgFilledPrice' in order_data:
            avg_price = float(order_data['avgFilledPrice'])
        filled_time = None
        if 'filledTime' in order_data:
            filled_time = pytz.timezone(settings.TIME_ZONE).localize(
                datetime.strptime(order_data['filledTime'], "%m/%d/%Y %H:%M:%S EDT"))
        placed_time = pytz.timezone(settings.TIME_ZONE).localize(
            datetime.strptime(order_data['placedTime'], "%m/%d/%Y %H:%M:%S EDT"))
        time_in_force = get_time_in_force_enum(order_data['timeInForce'])

        order = WebullOrder(
            order_id=order_id,
            ticker_id=ticker_id,
            symbol=symbol,
            action=action,
            status=status,
            total_quantity=total_quantity,
            filled_quantity=filled_quantity,
            price=price,
            avg_price=avg_price,
            filled_time=filled_time,
            placed_time=placed_time,
            time_in_force=time_in_force,
            paper=paper,
        )
        order.save()


def save_webull_order_note(order_id, note):
    order_note = WebullOrderNote(
        order_id=str(order_id),
        note=note,
    )
    order_note.save()


def save_hist_minute_bar(bar_data):
    bar = HistoricalMinuteBar.objects.filter(
        symbol=bar_data['symbol'], time=bar_data['time']).first()
    if not bar:
        bar = HistoricalMinuteBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            time=bar_data['time'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
            vwap=bar_data['vwap'],
        )
        bar.save()


def save_hist_daily_bar(bar_data):
    bar = HistoricalDailyBar.objects.filter(
        symbol=bar_data['symbol'], date=bar_data['date']).first()
    if not bar:
        bar = HistoricalDailyBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
        )
        bar.save()
