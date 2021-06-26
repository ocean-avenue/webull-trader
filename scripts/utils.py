import pandas as pd
import numpy as np
import pytz
import math
from django.utils import timezone
from django.conf import settings
from datetime import datetime, date
from scripts import config
from sdk import fmpsdk, webullsdk
from webull_trader import enums
from webull_trader.models import HistoricalKeyStatistics, HistoricalTopGainer, HistoricalTopLoser, OvernightPosition, OvernightTrade, StockQuote, SwingHistoricalDailyBar, TradingLog, TradingSettings, WebullAccountStatistics, WebullCredentials, WebullNews, WebullOrder, WebullOrderNote, HistoricalMinuteBar, HistoricalDailyBar

# sector values
BASIC_MATERIALS = "Basic Materials"
COMMUNICATION_SERVICES = "Communication Services"
CONSUMER_CYCLICAL = "Consumer Cyclical"
CONSUMER_DEFENSIVE = "Consumer Defensive"
ENERGY = "Energy"
FINANCIAL_SERVICES = "Financial Services"
HEALTHCARE = "Healthcare"
INDUSTRIALS = "Industrials"
REAL_ESTATE = "Real Estate"
TECHNOLOGY = "Technology"
UTILITIES = "Utilities"

MILLNAMES = ['', 'K', 'M', 'B', 'T']


def millify(n):
    if not n:
        return n
    n = float(n)
    millidx = max(0, min(len(MILLNAMES)-1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))
    return '{:.2f}{}'.format(n / 10**(3 * millidx), MILLNAMES[millidx])


def local_datetime(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    return localtz


def local_time_minute(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M'
    return localtz.strftime(format)


def local_time_minute_second(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M:%S'
    return localtz.strftime(format)


# hack to delay 1 minute


def local_time_minute_delay(t):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    hour = str(localtz.hour)
    minute = str(localtz.minute + 1)
    if minute == "60":
        minute = "00"
        hour = str(localtz.hour + 1)
    if len(hour) < 2:
        hour = "0{}".format(hour)
    if len(minute) < 2:
        minute = "0{}".format(minute)
    return "{}:{}".format(hour, minute)


# for multi minutes

def local_time_minute_scale(t, time_scale):
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    hour = str(localtz.hour)
    minute = localtz.minute + 1
    res = minute % time_scale
    minute -= res
    if res > 0:
        minute += time_scale
    minute = str(minute)
    if minute == "60":
        minute = "00"
        hour = str(localtz.hour + 1)
    if len(hour) < 2:
        hour = "0{}".format(hour)
    if len(minute) < 2:
        minute = "0{}".format(minute)
    return "{}:{}".format(hour, minute)


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
    # wait 2 min for webull get pre market data ready
    if now.hour == 4 and now.minute < 2:
        return False
    return True


def is_pre_market_hour_exact():
    """
    NY pre market hour from 04:00 to 09:30
    """
    now = datetime.now()
    if now.hour < 4 or now.hour > 9:
        return False
    if now.hour == 9 and now.minute >= 30:
        return False
    return True


def is_after_market_hour():
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    # wait 2 min for webull get after market data ready
    if now.hour == 16 and now.minute < 2:
        return False
    # stop after market earlier for 5 minutes
    if now.hour == 19 and now.minute >= 55:
        return False
    return True


def is_after_market_hour_exact():
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    return True


def is_regular_market_hour():
    """
    NY regular market hour from 09:30 to 16:00
    """
    now = datetime.now()
    if now.hour < 9 or now.hour >= 16:
        return False
    # wait 2 min for webull get regular market data ready
    if now.hour == 9 and now.minute < 32:
        return False
    # stop regular market earlier for 5 minutes
    if now.hour == 15 and now.minute >= 55:
        return False
    return True


def is_regular_market_hour_exact():
    """
    NY regular market hour from 09:30 to 16:00
    """
    now = datetime.now()
    if now.hour < 9 or now.hour >= 16:
        return False
    if now.hour == 9 and now.minute < 30:
        return False
    return True


def is_pre_market_time(t):
    if t.hour < 4 or t.hour > 9:
        return False
    if t.hour == 9 and t.minute >= 30:
        return False
    return True


def is_after_market_time(t):
    if t.hour < 16 or t.hour >= 20:
        return False
    return True


def is_regular_market_time(t):
    if t.hour < 9 or t.hour >= 16:
        return False
    if t.hour == 9 and t.minute < 30:
        return False
    return True


def get_trading_hour():
    if is_pre_market_hour_exact():
        return enums.TradingHourType.BEFORE_MARKET_OPEN
    elif is_after_market_hour_exact():
        return enums.TradingHourType.AFTER_MARKET_CLOSE
    elif is_regular_market_hour_exact():
        return enums.TradingHourType.REGULAR
    return None


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


def check_bars_updated(bars, time_scale=1):
    """
    check if have valid latest chart data, delay no more than 1 minute
    """
    latest_index = bars.index[-1]
    latest_timestamp = int(datetime.timestamp(latest_index.to_pydatetime()))
    current_timestamp = int(datetime.timestamp(datetime.now()))
    if current_timestamp - latest_timestamp <= 60 * time_scale:
        return True
    return False


def check_bars_continue(bars, time_scale=1, period=10):
    """
    check if candle bar is continue of time scale minutes
    """
    last_minute = -1
    is_continue = True
    period_bars = bars.tail(period)
    for index, _ in period_bars.iterrows():
        time = index.to_pydatetime()
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


def check_bars_has_volume(bars, time_scale=1, period=10):
    """
    check if bar chart has enough volume
    """
    has_volume = True
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    for index, row in period_bars.iterrows():
        time = index.to_pydatetime()
        confirm_volume = get_avg_confirm_volume(time) * time_scale
        volume = row["volume"]
        if volume < confirm_volume:
            has_volume = False
            break

    return has_volume


def check_bars_has_amount(bars, time_scale=1, period=10):
    """
    check if bar chart has enough amount
    """
    has_amount = True
    period_bars = bars.tail(period + 1)
    period_bars = period_bars.head(period)
    for index, row in period_bars.iterrows():
        time = index.to_pydatetime()
        confirm_amount = get_avg_confirm_amount(time) * time_scale
        volume = row["volume"]
        price = row["close"]
        if volume * price < confirm_amount:
            has_amount = False
            break

    return has_amount


def check_bars_has_long_wick_up(bars, count=1):
    """
    check if bar chart has long wick up
    """
    if len(bars) + 1 <= count:
        return False
    long_wick_up_count = 0
    for i in range(2, count + 2):
        candle = bars.iloc[-i]
        mid = max(candle["close"], candle["open"])
        high = candle["high"]
        low = candle["low"]
        if (mid - low) > 0 and (high - mid) / (mid - low) >= 2:
            long_wick_up_count += 1
    return long_wick_up_count >= count


def check_bars_rel_volume(bars):
    """
    check if bar chart relative volume
    """
    # check relative volume over 3
    last_candle = bars.iloc[-1]
    last_candle2 = bars.iloc[-2]
    last_candle3 = bars.iloc[-3]
    last_candle4 = bars.iloc[-4]

    if (last_candle["volume"] + last_candle2["volume"]) / (last_candle3["volume"] + last_candle4["volume"]) > get_min_relative_volume() or \
            last_candle["volume"] / last_candle2["volume"] > get_min_relative_volume() or last_candle2["volume"] / last_candle3["volume"] > get_min_relative_volume():
        # relative volume ok
        return True
    return False


def check_bars_volatility(bars):
    """
    check if has bar's ohlc has different price
    """
    period_bars = bars.tail(10)
    flat_count = 0
    price_set = set()
    for index, row in period_bars.iterrows():
        time = index.to_pydatetime()
        # check for pre market hour only
        if is_pre_market_hour_exact() and is_pre_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # check for after market hour only
        if is_after_market_hour_exact() and is_after_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # check for regular market hour only
        if is_regular_market_hour_exact() and is_regular_market_time(time):
            if row['open'] == row['close'] and row['close'] == row['high'] and row['high'] == row['low']:
                flat_count += 1
        # add price value set
        price_set.add(row['open'])
        price_set.add(row['high'])
        price_set.add(row['low'])
        price_set.add(row['close'])
    # price not like open: 7.35, high: 7.35, low: 7.35, close: 7.35
    if flat_count > 2:
        return False
    # price set only in a few values
    if len(price_set) <= 8:
        return False
    return True


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

        prev_open2 = bars.iloc[-2]['open']
        prev_open3 = bars.iloc[-3]['open']
        prev_open4 = bars.iloc[-4]['open']

        if prev_close2 == prev_close3 and prev_close3 == prev_close4 and \
                prev_open2 == prev_open3 and prev_open3 == prev_open4:
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


def get_hist_key_stat(symbol, date):
    key_statistics = HistoricalKeyStatistics.objects.filter(
        symbol=symbol).filter(date=date).first()
    return key_statistics


def get_hist_top_gainer(symbol, date):
    top_gainer = HistoricalTopGainer.objects.filter(
        symbol=symbol).filter(date=date).first()
    return top_gainer


def get_hist_top_loser(symbol, date):
    top_loser = HistoricalTopLoser.objects.filter(
        symbol=symbol).filter(date=date).first()
    return top_loser


def get_order_action_enum(action_str):
    action = enums.ActionType.BUY
    if action_str == "SELL":
        action = enums.ActionType.SELL
    return action


def get_order_type_enum(type_str):
    order_type = enums.OrderType.LMT
    if type_str == "MKT":
        order_type = enums.OrderType.MKT
    elif type_str == "STP":
        order_type = enums.OrderType.STP
    elif type_str == "STP LMT":
        order_type = enums.OrderType.STP_LMT
    elif type_str == "STP TRAIL":
        order_type = enums.OrderType.STP_TRAIL
    return order_type


def get_time_in_force_enum(time_in_force_str):
    time_in_force = enums.TimeInForceType.GTC
    if time_in_force_str == "DAY":
        time_in_force = enums.TimeInForceType.DAY
    elif time_in_force_str == "IOC":
        time_in_force = enums.TimeInForceType.IOC
    return time_in_force


def check_paper():
    settings = TradingSettings.objects.first()
    if not settings:
        print(
            "[{}] Cannot find trading settings, default paper trading!".format(get_now()))
        return False
    return settings.paper


def get_algo_type():
    settings = TradingSettings.objects.first()
    if settings == None:
        print("[{}] Cannot find trading settings, default algo type!".format(get_now()))
        return enums.AlgorithmType.DAY_MOMENTUM
    return settings.algo_type


def get_avg_confirm_volume(time):
    settings = TradingSettings.objects.first()
    if settings == None:
        print(
            "[{}] Cannot find trading settings, default confirm volume!".format(get_now()))
        return 6000
    if is_pre_market_time(time) or is_after_market_time(time):
        return settings.extended_avg_confirm_volume
    return settings.avg_confirm_volume


def get_avg_confirm_amount(time):
    settings = TradingSettings.objects.first()
    if settings == None:
        print(
            "[{}] Cannot find trading settings, default confirm amount!".format(get_now()))
        return 30000
    if is_pre_market_time(time) or is_after_market_time(time):
        return settings.extended_avg_confirm_amount
    return settings.avg_confirm_amount


def get_min_relative_volume():
    settings = TradingSettings.objects.first()
    if settings == None:
        print(
            "[{}] Cannot find trading settings, default relative volume!".format(get_now()))
        return 3
    return settings.min_relative_volume


def get_webull_order_time(order_time):
    time_fmt = "%m/%d/%Y %H:%M:%S EDT"
    if "EST" in order_time:
        time_fmt = "%m/%d/%Y %H:%M:%S EST"
    return pytz.timezone(settings.TIME_ZONE).localize(datetime.strptime(order_time, time_fmt))


def load_webull_credentials(cred_data, paper=True):
    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        credentials = WebullCredentials(
            cred=cred_data,
            paper=paper,
        )
    else:
        credentials.cred = cred_data
    credentials.save()


def save_webull_credentials(cred_data, paper=True):
    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        credentials = WebullCredentials(
            cred=cred_data,
            paper=paper,
        )
    else:
        credentials.cred = cred_data
    credentials.save()


def save_webull_account(acc_data, paper=True):
    today = date.today()
    print("[{}] Importing daily account status ({})...".format(
        get_now(), today.strftime("%Y-%m-%d")))
    if paper:
        if "accountMembers" in acc_data:
            account_members = acc_data['accountMembers']
            day_profit_loss = 0
            for account_member in account_members:
                if account_member['key'] == 'dayProfitLoss':
                    day_profit_loss = float(account_member['value'])
            acc_stat = WebullAccountStatistics.objects.filter(
                date=today).first()
            if not acc_stat:
                acc_stat = WebullAccountStatistics(date=today)
            acc_stat.net_liquidation = float(acc_data['netLiquidation'])
            acc_stat.total_profit_loss = float(acc_data['totalProfitLoss'])
            acc_stat.total_profit_loss_rate = float(
                acc_data['totalProfitLossRate'])
            acc_stat.day_profit_loss = day_profit_loss
            acc_stat.save()
    else:
        if "accountMembers" in acc_data:
            account_members = acc_data['accountMembers']
            acc_stat = WebullAccountStatistics.objects.filter(
                date=today).first()
            if not acc_stat:
                acc_stat = WebullAccountStatistics(date=today)
            acc_stat.net_liquidation = float(acc_data['netLiquidation'])
            # get today's P&L
            daily_pl = webullsdk.get_daily_profitloss()
            day_profit_loss = 0
            if len(daily_pl) > 0:
                today_pl = daily_pl[-1]
                if today_pl['periodName'] == today.strftime("%Y-%m-%d"):
                    day_profit_loss = float(today_pl['profitLoss'])
            acc_stat.total_profit_loss = acc_stat.total_profit_loss or 0
            acc_stat.total_profit_loss_rate = acc_stat.total_profit_loss_rate or 0
            acc_stat.day_profit_loss = day_profit_loss
            acc_stat.save()
            # update total profit loss
            all_acc_stats = WebullAccountStatistics.objects.all()
            total_profit_loss = 0
            for acc in all_acc_stats:
                total_profit_loss += acc.day_profit_loss
            acc_stat.total_profit_loss = total_profit_loss
            if (acc_stat.net_liquidation - acc_stat.total_profit_loss) != 0:
                acc_stat.total_profit_loss_rate = acc_stat.total_profit_loss / \
                    (acc_stat.net_liquidation - acc_stat.total_profit_loss)
            acc_stat.save()


def save_webull_order(order_data, paper=True):
    create_order = False
    if paper:
        order_id = str(order_data['orderId'])
        order = WebullOrder.objects.filter(order_id=order_id).first()
        symbol = order_data['ticker']['symbol']
        print("[{}] Importing order <{}> {} ({})...".format(
            get_now(), symbol, order_id, order_data['placedTime']))
        if order:
            print("[{}] Order <{}> {} ({}) already existed!".format(
                get_now(), symbol, order_id, order_data['placedTime']))
        else:
            ticker_id = str(order_data['ticker']['tickerId'])
            action = get_order_action_enum(order_data['action'])
            status = order_data['statusStr']
            order_type = get_order_type_enum(order_data['orderType'])
            total_quantity = int(order_data['totalQuantity'])
            filled_quantity = int(order_data['filledQuantity'])
            avg_price = 0
            if 'avgFilledPrice' in order_data:
                avg_price = float(order_data['avgFilledPrice'])
                price = avg_price
            if 'lmtPrice' in order_data:
                price = float(order_data['lmtPrice'])
            filled_time = None
            if 'filledTime' in order_data:
                filled_time = get_webull_order_time(order_data['filledTime'])
            placed_time = get_webull_order_time(order_data['placedTime'])
            time_in_force = get_time_in_force_enum(order_data['timeInForce'])
            create_order = True
    else:
        order_obj = order_data['orders'][0]
        order_id = str(order_obj['orderId'])
        order = WebullOrder.objects.filter(order_id=order_id).first()
        symbol = order_obj['ticker']['symbol']
        print("[{}] Importing order <{}> {} ({})...".format(
            get_now(), symbol, order_id, order_obj['createTime']))
        if order:
            print("[{}] Order <{}> {} ({}) already existed!".format(
                get_now(), symbol, order_id, order_obj['createTime']))
        else:
            ticker_id = str(order_obj['ticker']['tickerId'])
            action = get_order_action_enum(order_obj['action'])
            status = order_obj['statusStr']
            order_type = get_order_type_enum(order_obj['orderType'])
            total_quantity = int(order_obj['totalQuantity'])
            filled_quantity = int(order_obj['filledQuantity'])
            avg_price = 0.0
            price = 0.0
            if 'avgFilledPrice' in order_obj:
                avg_price = float(order_obj['avgFilledPrice'])
                price = avg_price
            if 'lmtPrice' in order_obj:
                price = float(order_obj['lmtPrice'])
            if 'auxPrice' in order_obj:  # for stop order
                price = float(order_obj['auxPrice'])
            filled_time = None
            if 'filledTime' in order_obj:
                filled_time = get_webull_order_time(order_obj['filledTime'])
            placed_time = get_webull_order_time(order_obj['createTime'])
            time_in_force = get_time_in_force_enum(order_obj['timeInForce'])
            create_order = True

    if create_order:
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
            order_type=order_type,
            filled_time=filled_time,
            placed_time=placed_time,
            time_in_force=time_in_force,
            paper=paper,
        )
        order.save()


def save_webull_order_note(order_id, setup=enums.SetupType.DAY_FIRST_CANDLE_NEW_HIGH, note=""):
    order_note = WebullOrderNote(
        order_id=str(order_id),
        setup=setup,
        note=note,
    )
    order_note.save()


def save_webull_news_list(news_list, symbol, date):
    print("[{}] Importing news for {}...".format(get_now(), symbol))
    for news_data in news_list:
        save_webull_news(news_data, symbol, date)


def save_webull_news(news_data, symbol, date):
    news = WebullNews.objects.filter(
        news_id=news_data['id'], symbol=symbol, date=date).first()
    if not news:
        news = WebullNews(
            news_id=news_data['id'],
            symbol=symbol,
            title=news_data['title'],
            source_name=news_data['sourceName'],
            collect_source=news_data['collectSource'],
            news_time=news_data['newsTime'],
            summary=news_data['summary'],
            news_url=news_data['newsUrl'],
            date=date,
        )
        news.save()


def save_trading_log(text, tag, trading_hour, date):
    log = TradingLog.objects.filter(date=date).filter(
        tag=tag).filter(trading_hour=trading_hour).first()
    if log == None:
        log = TradingLog(
            date=date,
            tag=tag,
            trading_hour=trading_hour,
        )
    log.log_text = text
    log.save()


def save_hist_key_statistics(quote_data, date):
    if 'symbol' not in quote_data:
        return
    symbol = quote_data['symbol']
    print("[{}] Importing key statistics for {}...".format(
        get_now(), symbol))
    key_statistics = get_hist_key_stat(symbol, date)
    if not key_statistics:
        market_value = 0
        if 'marketValue' in quote_data:
            market_value = float(quote_data['marketValue'])
        pe = None
        if 'pe' in quote_data:
            pe = float(quote_data['pe'])
        forward_pe = None
        if 'forwardPe' in quote_data:
            forward_pe = float(quote_data['forwardPe'])
        pe_ttm = None
        if 'peTtm' in quote_data:
            pe_ttm = float(quote_data['peTtm'])
        eps = None
        if 'eps' in quote_data:
            eps = float(quote_data['eps'])
        eps_ttm = None
        if 'epsTtm' in quote_data:
            eps_ttm = float(quote_data['epsTtm'])
        pb = None
        if 'pb' in quote_data:
            pb = float(quote_data['pb'])
        ps = None
        if 'ps' in quote_data:
            ps = float(quote_data['ps'])
        bps = None
        if 'bps' in quote_data:
            bps = float(quote_data['bps'])
        turnover_rate = None
        if 'turnoverRate' in quote_data and quote_data['turnoverRate'] != "-" and quote_data['turnoverRate'] != None:
            turnover_rate = float(quote_data['turnoverRate'])
        vibrate_ratio = None
        if 'vibrateRatio' in quote_data and quote_data['vibrateRatio'] != "-" and quote_data['vibrateRatio'] != None:
            vibrate_ratio = float(quote_data['vibrateRatio'])
        latest_earnings_date = ''
        if 'latestEarningsDate' in quote_data:
            latest_earnings_date = quote_data['latestEarningsDate']
        estimate_earnings_date = ''
        if 'estimateEarningsDate' in quote_data:
            estimate_earnings_date = quote_data['estimateEarningsDate']
        total_shares = None
        if 'totalShares' in quote_data and quote_data['totalShares'] != "-" and quote_data['totalShares'] != None:
            total_shares = float(quote_data['totalShares'])
        outstanding_shares = None
        if 'outstandingShares' in quote_data and quote_data['outstandingShares'] != "-" and quote_data['outstandingShares'] != None:
            outstanding_shares = float(quote_data['outstandingShares'])
        short_float = None
        if 'shortFloat' in quote_data and quote_data['shortFloat'] != "-" and quote_data['shortFloat'] != None:
            short_float = float(quote_data['shortFloat'])
        key_statistics = HistoricalKeyStatistics(
            symbol=symbol,
            open=float(quote_data['open']),
            high=float(quote_data['high']),
            low=float(quote_data['low']),
            close=float(quote_data['close']),
            change=float(quote_data['change']),
            change_ratio=float(quote_data['changeRatio']),
            market_value=market_value,
            volume=float(quote_data['volume']),
            turnover_rate=turnover_rate,
            vibrate_ratio=vibrate_ratio,
            avg_vol_10d=float(quote_data['avgVol10D']),
            avg_vol_3m=float(quote_data['avgVol3M']),
            pe=pe,
            forward_pe=forward_pe,
            pe_ttm=pe_ttm,
            eps=eps,
            eps_ttm=eps_ttm,
            pb=pb,
            ps=ps,
            bps=bps,
            short_float=short_float,
            total_shares=total_shares,
            outstanding_shares=outstanding_shares,
            fifty_two_wk_high=float(quote_data['fiftyTwoWkHigh']),
            fifty_two_wk_low=float(quote_data['fiftyTwoWkLow']),
            latest_earnings_date=latest_earnings_date,
            estimate_earnings_date=estimate_earnings_date,
            date=date,
        )
        key_statistics.save()


def save_hist_top_gainer(gainer_data, date):
    symbol = gainer_data['symbol']
    print("[{}] Importing top gainer for {}...".format(
        get_now(), symbol))
    top_gainer = get_hist_top_gainer(symbol, date)
    if not top_gainer:
        top_gainer = HistoricalTopGainer(
            symbol=symbol,
            date=date,
        )
    top_gainer.ticker_id = gainer_data['ticker_id']
    top_gainer.change = gainer_data['change']
    top_gainer.change_percentage = gainer_data['change_percentage']
    top_gainer.price = gainer_data['close']
    top_gainer.save()


def save_hist_top_loser(loser_data, date):
    symbol = loser_data['symbol']
    print("[{}] Importing top loser for {}...".format(
        get_now(), symbol))
    top_loser = get_hist_top_loser(symbol, date)
    if not top_loser:
        top_loser = HistoricalTopLoser(
            symbol=symbol,
            date=date,
        )
    top_loser.ticker_id = loser_data['ticker_id']
    top_loser.change = loser_data['change']
    top_loser.change_percentage = loser_data['change_percentage']
    top_loser.price = loser_data['close']
    top_loser.save()


def save_hist_minute_bar_list(bar_list):
    print("[{}] Importing minute bar for {}...".format(
        get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_hist_minute_bar(bar_data)


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


def save_hist_daily_bar_list(bar_list):
    print("[{}] Importing daily bar for {}...".format(
        get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_hist_daily_bar(bar_data)


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


def save_swing_hist_daily_bar_list(bar_list):
    print("[{}] Importing swing daily bar for {}...".format(
        get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_swing_hist_daily_bar(bar_data)


def save_swing_hist_daily_bar(bar_data):
    bar = SwingHistoricalDailyBar.objects.filter(
        symbol=bar_data['symbol'], date=bar_data['date']).first()
    if not bar:
        bar = SwingHistoricalDailyBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
            rsi_10=bar_data['rsi_10'],
            sma_55=bar_data['sma_55'],
            sma_120=bar_data['sma_120'],
        )
        bar.save()


def save_overnight_position(symbol, ticker_id, order_id, setup, cost, quant, buy_time):
    position = OvernightPosition.objects.filter(order_id=order_id).first()
    if not position:
        position = OvernightPosition(order_id=order_id)
    position.symbol = symbol
    position.ticker_id = ticker_id
    position.setup = setup
    position.cost = cost
    position.quantity = quant
    position.buy_time = buy_time
    position.buy_date = buy_time.date()
    position.save()


def save_overnight_trade(symbol, position, order_id, sell_price, sell_time):
    trade = OvernightTrade.objects.filter(sell_order_id=order_id).first()
    if not trade:
        trade = OvernightTrade(sell_order_id=order_id)
    trade.symbol = symbol
    trade.quantity = position.quantity
    trade.buy_date = position.buy_date
    trade.buy_time = position.buy_time
    trade.buy_price = position.cost
    trade.buy_order_id = position.order_id
    trade.sell_time = sell_time
    trade.sell_date = sell_time.date()
    trade.sell_price = sell_price
    trade.sell_order_id = order_id
    trade.setup = position.setup
    trade.save()


def fetch_stock_quotes(symbol_list):
    if len(symbol_list) == 0:
        return
    # fmp use '-', webull use ' ', e.g LGF-A, LGF A
    fmp_symbol_list = []
    for symbol in symbol_list:
        fmp_symbol_list.append(symbol.replace(' ', '-'))
    quotes = fmpsdk.get_quotes(fmp_symbol_list)
    quote_dist = {}
    for quote in quotes:
        quote_dist[quote["symbol"]] = quote
    profiles = fmpsdk.get_profiles(fmp_symbol_list)
    profile_dist = {}
    for profile in profiles:
        profile_dist[profile["symbol"]] = profile

    # save stock quote
    for symbol in symbol_list:
        fmp_symbol = symbol.replace(' ', '-')
        if fmp_symbol not in quote_dist:
            continue
        quote = quote_dist[fmp_symbol]
        stock_quote = StockQuote.objects.filter(symbol=symbol).first()
        if not stock_quote:
            stock_quote = StockQuote(symbol=symbol)
        stock_quote.price = quote["price"]
        stock_quote.volume = quote["volume"]
        stock_quote.change = quote["change"]
        stock_quote.change_percentage = quote["changesPercentage"]
        stock_quote.market_value = quote["marketCap"]
        stock_quote.avg_price_50d = quote["priceAvg50"]
        stock_quote.avg_price_200d = quote["priceAvg200"]
        stock_quote.avg_volume = quote["avgVolume"]
        stock_quote.exchange = quote["exchange"]
        stock_quote.eps = quote["eps"]
        stock_quote.pe = quote["pe"]
        stock_quote.outstanding_shares = quote["sharesOutstanding"]
        if fmp_symbol in profile_dist:
            profile = profile_dist[fmp_symbol]
            stock_quote.beta = profile["beta"]
            stock_quote.last_div = profile["lastDiv"]
            stock_quote.price_range = profile["range"]
            stock_quote.sector = profile["sector"]
            stock_quote.industry = profile["industry"]
            stock_quote.is_etf = profile["isEtf"]
        stock_quote.save()


def check_day_trade_order(setup):
    if setup == enums.SetupType.DAY_10_CANDLES_NEW_HIGH or setup == enums.SetupType.DAY_20_CANDLES_NEW_HIGH or \
            setup == enums.SetupType.DAY_30_CANDLES_NEW_HIGH or setup == enums.SetupType.DAY_BULL_FLAG or \
            setup == enums.SetupType.DAY_FIRST_CANDLE_NEW_HIGH or setup == enums.SetupType.DAY_GAP_AND_GO or \
            setup == enums.SetupType.DAY_RED_TO_GREEN or setup == enums.SetupType.DAY_REVERSAL or \
            setup == enums.SetupType.DAY_EARNINGS_GAP:
        return True
    return False


def check_swing_trade_algo(algo):
    if algo == enums.AlgorithmType.SWING_TURTLE_20 or algo == enums.AlgorithmType.SWING_TURTLE_55 or \
            algo == enums.AlgorithmType.DAY_SWING_BREAKOUT_TURTLE or algo == enums.AlgorithmType.DAY_SWING_RG_TURTLE or \
            algo == enums.AlgorithmType.DAY_SWING_EARNINGS_TURTLE or algo == enums.AlgorithmType.DAY_SWING_MOMO_TURTLE:
        return True
    return False


def get_day_trade_orders(date=None, symbol=None):
    # only limit orders for day trades
    lmt_buy_orders = WebullOrder.objects.filter(order_type=enums.OrderType.LMT).filter(
        status="Filled").filter(action=enums.ActionType.BUY)
    lmt_sell_orders = WebullOrder.objects.filter(order_type=enums.OrderType.LMT).filter(
        status="Filled").filter(action=enums.ActionType.SELL)
    if date:
        lmt_buy_orders = lmt_buy_orders.filter(filled_time__year=date.year,
                                               filled_time__month=date.month, filled_time__day=date.day)
        lmt_sell_orders = lmt_sell_orders.filter(filled_time__year=date.year, filled_time__month=date.month,
                                                 filled_time__day=date.day)
    if symbol:
        lmt_buy_orders = lmt_buy_orders.filter(symbol=symbol)
        lmt_sell_orders = lmt_sell_orders.filter(symbol=symbol)
    buy_orders = []
    for order in lmt_buy_orders:
        if check_day_trade_order(order.setup):
            buy_orders.append(order)
    sell_orders = []
    for order in lmt_sell_orders:
        if check_day_trade_order(order.setup):
            sell_orders.append(order)
    return (buy_orders, sell_orders)


def get_trades_from_orders(buy_orders, sell_orders):
    trades = []
    for buy_order in buy_orders:
        # fill buy side
        trades.append({
            "symbol": buy_order.symbol,
            "ticker_id": buy_order.ticker_id,
            "quantity": buy_order.filled_quantity,
            "buy_price": buy_order.avg_price,
            "buy_time": buy_order.filled_time,
            "buy_order_id": buy_order.order_id,
        })
    for sell_order in sell_orders:
        # fill sell side
        for trade in trades:
            if sell_order.symbol == trade["symbol"] and sell_order.filled_quantity == trade["quantity"] and "sell_price" not in trade:
                trade["sell_price"] = sell_order.avg_price
                trade["sell_time"] = sell_order.filled_time
                trade["sell_order_id"] = sell_order.order_id
                break
    return trades


def get_stats_empty_list(size=8):
    empty_list = []
    for _ in range(0, size):
        empty_list.append({
            "trades": 0,
            "win_trades": 0,
            "loss_trades": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "profit_loss": 0.0,
        })
    return empty_list


def get_entry_price_range_labels():
    return [
        "$0-$1",  # 0
        "$1-$2",  # 1
        "$2-$3",  # 2
        "$3-$4",  # 3
        "$4-$5",  # 4
        "$5-$6",  # 5
        "$6-$7",  # 6
        "$7-$8",  # 7
        "$8-$9",  # 8
        "$9-$10",  # 9
        "$10-$15",  # 10
        "$15-$20",  # 11
        "$20-$50",  # 12
        "$50-$100",  # 13
        "$100-$200",  # 14
        "$200+",  # 15
    ]


def get_entry_price_range_index(p):
    index = -1
    if p <= 1:
        index = 0
    elif p <= 2:
        index = 1
    elif p <= 3:
        index = 2
    elif p <= 4:
        index = 3
    elif p <= 5:
        index = 4
    elif p <= 6:
        index = 5
    elif p <= 7:
        index = 6
    elif p <= 8:
        index = 7
    elif p <= 9:
        index = 8
    elif p <= 10:
        index = 9
    elif p <= 15:
        index = 10
    elif p <= 20:
        index = 11
    elif p <= 50:
        index = 12
    elif p <= 100:
        index = 13
    elif p <= 200:
        index = 14
    else:
        index = 15
    return index


def get_market_cap_range_labels():
    return [
        "0-50M (Nano Cap)",  # 0
        "50M-300M (Micro Cap)",  # 1
        "300M-2B (Small Cap)",  # 2
        "2B-10B (Mid Cap)",  # 3
        "10B-200B (Large Cap)",  # 4
        "200B+ (Mega Cap)",  # 5
    ]


def get_market_cap_range_index(mktcap):
    index = -1
    if mktcap <= 50000000:
        index = 0
    elif mktcap <= 300000000:
        index = 1
    elif mktcap <= 2000000000:
        index = 2
    elif mktcap <= 10000000000:
        index = 3
    elif mktcap <= 200000000000:
        index = 4
    else:
        index = 5
    return index


def get_free_float_range_labels():
    return [
        "None",  # 0
        "0-1M",  # 1
        "1M-5M",  # 2
        "5M-10M",  # 3
        "10M-20M",  # 4
        "20M-50M",  # 5
        "50M-100M",  # 6
        "100M-200M",  # 7
        "200M-500M",  # 8
        "500M-1B",  # 9
        "1B+",  # 10
    ]


def get_free_float_range_index(free_float):
    index = -1
    if free_float == None:
        index = 0
    elif free_float <= 1000000:
        index = 1
    elif free_float <= 5000000:
        index = 2
    elif free_float <= 10000000:
        index = 3
    elif free_float <= 20000000:
        index = 4
    elif free_float <= 50000000:
        index = 5
    elif free_float <= 100000000:
        index = 6
    elif free_float <= 200000000:
        index = 7
    elif free_float <= 500000000:
        index = 8
    elif free_float <= 1000000000:
        index = 9
    else:
        index = 10
    return index


def get_turnover_ratio_range_labels():
    return [
        "None",  # 0
        "0-10%",  # 1
        "10-20%",  # 2
        "20-40%",  # 3
        "40-60%",  # 4
        "60-80%",  # 5
        "80-100%",  # 6
        "100-200%",  # 7
        "200-500%",  # 8
        "500-1000%",  # 9
        "1000%+",  # 10
    ]


def get_turnover_ratio_range_index(turnover):
    index = -1
    if turnover == None:
        index = 0
    elif turnover <= 0.1:
        index = 1
    elif turnover <= 0.2:
        index = 2
    elif turnover <= 0.4:
        index = 3
    elif turnover <= 0.6:
        index = 4
    elif turnover <= 0.8:
        index = 5
    elif turnover <= 1:
        index = 6
    elif turnover <= 2:
        index = 7
    elif turnover <= 5:
        index = 8
    elif turnover <= 10:
        index = 9
    else:
        index = 10
    return index


def get_short_float_range_labels():
    return [
        "None",  # 0
        "0-5%",  # 1
        "5-10%",  # 2
        "10-15%",  # 3
        "15-20%",  # 4
        "20-25%",  # 5
        "25-30%",  # 6
        "30%+",  # 7
    ]


def get_short_float_range_index(short_float):
    index = -1
    if short_float == None:
        index = 0
    elif short_float <= 5:
        index = 1
    elif short_float <= 10:
        index = 2
    elif short_float <= 15:
        index = 3
    elif short_float <= 20:
        index = 4
    elif short_float <= 25:
        index = 5
    elif short_float <= 30:
        index = 6
    else:
        index = 7
    return index


def get_gap_range_labels():
    return [
        "Down 15%+",  # 0
        "Down 10-15%",  # 1
        "Down 7-10%",  # 2
        "Down 5-7%",  # 3
        "Down 3-5%",  # 4
        "Down 1-3%",  # 5
        "Down 0-1%",  # 6
        "Up 0-1%",  # 7
        "Up 1-3%",  # 8
        "Up 3-5%",  # 9
        "Up 5-7%",  # 10
        "Up 7-10%",  # 11
        "Up 10-15%",  # 12
        "Up 15%+",  # 13
    ]


def get_gap_range_index(gap):
    index = -1
    if gap <= -15:
        index = 0
    elif gap <= -10:
        index = 1
    elif gap <= -7:
        index = 2
    elif gap <= -5:
        index = 3
    elif gap <= -3:
        index = 4
    elif gap <= -1:
        index = 5
    elif gap <= 0:
        index = 6
    elif gap <= 1:
        index = 7
    elif gap <= 3:
        index = 8
    elif gap <= 5:
        index = 9
    elif gap <= 7:
        index = 10
    elif gap <= 10:
        index = 11
    elif gap <= 15:
        index = 12
    else:
        index = 13
    return index


def get_holding_time_labels():
    return [
        "0-30s",  # 0
        "30-60s",  # 1
        "1-2m",  # 2
        "2-3m",  # 3
        "3-4m",  # 4
        "4-5m",  # 5
        "5-6m",  # 6
        "6-7m",  # 7
        "7-8m",  # 8
        "8-9m",  # 9
        "9-10m",  # 10
        "10-12m",  # 11
        "12-15m",  # 12
        "15m+",  # 13
    ]


def get_holding_time_index(holding_sec):
    index = -1
    if holding_sec <= 30:
        index = 0
    elif holding_sec <= 60:
        index = 1
    elif holding_sec <= 120:
        index = 2
    elif holding_sec <= 180:
        index = 3
    elif holding_sec <= 240:
        index = 4
    elif holding_sec <= 300:
        index = 5
    elif holding_sec <= 360:
        index = 6
    elif holding_sec <= 420:
        index = 7
    elif holding_sec <= 480:
        index = 8
    elif holding_sec <= 540:
        index = 9
    elif holding_sec <= 600:
        index = 10
    elif holding_sec <= 720:
        index = 11
    elif holding_sec <= 900:
        index = 12
    else:
        index = 13
    return index


def get_relative_volume_labels():
    return [
        "0-0.5",  # 0
        "0.5-1",  # 1
        "1-1.5",  # 2
        "1.5-2",  # 3
        "2-3",  # 4
        "3-5",  # 5
        "5-10",  # 6
        "10+",  # 7
    ]


def get_relative_volume_index(rel_vol):
    index = -1
    if rel_vol <= 0.5:
        index = 0
    elif rel_vol <= 1:
        index = 1
    elif rel_vol <= 1.5:
        index = 2
    elif rel_vol <= 2:
        index = 3
    elif rel_vol <= 3:
        index = 4
    elif rel_vol <= 5:
        index = 5
    elif rel_vol <= 10:
        index = 6
    else:
        index = 7
    return index


def get_sector_labels():
    return [
        BASIC_MATERIALS,  # 0
        COMMUNICATION_SERVICES,  # 1
        CONSUMER_CYCLICAL,  # 2
        CONSUMER_DEFENSIVE,  # 3
        ENERGY,  # 4
        FINANCIAL_SERVICES,  # 5
        HEALTHCARE,  # 6
        INDUSTRIALS,  # 7
        REAL_ESTATE,  # 8
        TECHNOLOGY,  # 9
        UTILITIES,  # 10
        "None",  # 11
    ]


def get_sector_index(sector):
    index = -1
    if sector == BASIC_MATERIALS:
        index = 0
    elif sector == COMMUNICATION_SERVICES:
        index = 1
    elif sector == CONSUMER_CYCLICAL:
        index = 2
    elif sector == CONSUMER_DEFENSIVE:
        index = 3
    elif sector == ENERGY:
        index = 4
    elif sector == FINANCIAL_SERVICES:
        index = 5
    elif sector == HEALTHCARE:
        index = 6
    elif sector == INDUSTRIALS:
        index = 7
    elif sector == REAL_ESTATE:
        index = 8
    elif sector == TECHNOLOGY:
        index = 9
    elif sector == UTILITIES:
        index = 10
    elif sector == None:
        index = 11
    return index


def get_market_hourly_interval_labels():
    return [
        "04:00-04:30",  # 0
        "04:30-05:00",  # 1
        "05:00-05:30",  # 2
        "05:30-06:00",  # 3
        "06:00-06:30",  # 4
        "06:30-07:00",  # 5
        "07:00-07:30",  # 6
        "07:30-08:00",  # 7
        "08:00-08:30",  # 8
        "08:30-09:00",  # 9
        "09:00-09:30",  # 10
        "09:30-10:00",  # 11
        "10:00-10:30",  # 12
        "10:30-11:00",  # 13
        "11:00-11:30",  # 14
        "11:30-12:00",  # 15
        "12:00-12:30",  # 16
        "12:30-13:00",  # 17
        "13:00-13:30",  # 18
        "13:30-14:00",  # 19
        "14:00-14:30",  # 20
        "14:30-15:00",  # 21
        "15:00-15:30",  # 22
        "15:30-16:00",  # 23
        "16:00-16:30",  # 24
        "16:30-17:00",  # 25
        "17:00-17:30",  # 26
        "17:30-18:00",  # 27
        "18:00-18:30",  # 28
        "18:30-19:00",  # 29
        "19:00-19:30",  # 30
        "19:30-20:00",  # 31
    ]


def get_market_hourly_interval_index(t):
    index = -1
    if t.hour == 4:
        if t.minute < 30:
            index = 0
        else:
            index = 1
    elif t.hour == 5:
        if t.minute < 30:
            index = 2
        else:
            index = 3
    elif t.hour == 6:
        if t.minute < 30:
            index = 4
        else:
            index = 5
    elif t.hour == 7:
        if t.minute < 30:
            index = 6
        else:
            index = 7
    elif t.hour == 8:
        if t.minute < 30:
            index = 8
        else:
            index = 9
    elif t.hour == 9:
        if t.minute < 30:
            index = 10
        else:
            index = 11
    elif t.hour == 10:
        if t.minute < 30:
            index = 12
        else:
            index = 13
    elif t.hour == 11:
        if t.minute < 30:
            index = 14
        else:
            index = 15
    elif t.hour == 12:
        if t.minute < 30:
            index = 16
        else:
            index = 17
    elif t.hour == 13:
        if t.minute < 30:
            index = 18
        else:
            index = 19
    elif t.hour == 14:
        if t.minute < 30:
            index = 20
        else:
            index = 21
    elif t.hour == 15:
        if t.minute < 30:
            index = 22
        else:
            index = 23
    elif t.hour == 16:
        if t.minute < 30:
            index = 24
        else:
            index = 25
    elif t.hour == 17:
        if t.minute < 30:
            index = 26
        else:
            index = 27
    elif t.hour == 18:
        if t.minute < 30:
            index = 28
        else:
            index = 29
    elif t.hour == 19:
        if t.minute < 30:
            index = 30
        else:
            index = 31
    return index


def get_minute_candle_high_by_time_minute(candle_data, time):
    # candle_data = {
    #     "times": ...,
    #     "candles": ...,
    #     "volumes": ...,
    #     ...
    # }
    idx = 0
    for i in range(0, len(candle_data['times'])):
        if candle_data['times'][i] == time:
            idx = i
            break
    return candle_data['candles'][idx][3]


def get_trade_stat_dist_from_day_trades(day_trades):
    trades_dist = {}
    for trade in day_trades:
        if "sell_price" in trade:
            symbol = trade["symbol"]
            gain = round(
                (trade["sell_price"] - trade["buy_price"]) * trade["quantity"], 2)
            # build trades_dist
            if symbol not in trades_dist:
                trades_dist[symbol] = {
                    "trades": 0,
                    "win_trades": 0,
                    "loss_trades": 0,
                    "total_gain": 0,
                    "total_loss": 0,
                    "profit_loss": 0,
                    "total_cost": 0,
                    "top_gain": 0,
                    "top_loss": 0,
                }
            trades_dist[symbol]["trades"] += 1
            trades_dist[symbol]["profit_loss"] += gain
            trades_dist[symbol]["total_cost"] += trade["buy_price"]
            if gain > 0:
                trades_dist[symbol]["win_trades"] += 1
                trades_dist[symbol]["total_gain"] += gain
            else:
                trades_dist[symbol]["loss_trades"] += 1
                trades_dist[symbol]["total_loss"] += gain
            if gain > trades_dist[symbol]["top_gain"]:
                trades_dist[symbol]["top_gain"] = gain
            if gain < trades_dist[symbol]["top_loss"]:
                trades_dist[symbol]["top_loss"] = gain
    return trades_dist


def get_trade_stat_dist_from_swing_trades(swing_trades):
    trades_dist = {}
    for trade in swing_trades:
        symbol = trade.symbol
        buy_price = trade.buy_price
        sell_price = trade.sell_price
        quantity = trade.quantity
        total_cost = buy_price * quantity
        total_sold = sell_price * quantity
        gain = round((sell_price - buy_price) * quantity, 2)
        # build trades_dist
        if symbol not in trades_dist:
            trades_dist[symbol] = {
                "trades": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "total_gain": 0,
                "total_loss": 0,
                "profit_loss": 0,
                "total_cost": 0,
                "total_sold": 0,
                "top_gain": 0,
                "top_loss": 0,
            }
        trades_dist[symbol]["trades"] += 1
        trades_dist[symbol]["profit_loss"] += gain
        trades_dist[symbol]["total_cost"] += total_cost
        trades_dist[symbol]["total_sold"] += total_sold
        if gain > 0:
            trades_dist[symbol]["win_trades"] += 1
            trades_dist[symbol]["total_gain"] += gain
        else:
            trades_dist[symbol]["loss_trades"] += 1
            trades_dist[symbol]["total_loss"] += gain
        if gain > trades_dist[symbol]["top_gain"]:
            trades_dist[symbol]["top_gain"] = gain
        if gain < trades_dist[symbol]["top_loss"]:
            trades_dist[symbol]["top_loss"] = gain
    return trades_dist


def get_swing_daily_candle_high_by_date(symbol, date):
    day_bar = SwingHistoricalDailyBar.objects.filter(
        symbol=symbol).filter(date=date).first()
    if day_bar:
        return day_bar.high
    return 0


def get_gap_by_symbol_date(symbol, date):
    hist_daily_bars = HistoricalDailyBar.objects.filter(symbol=symbol)
    day_index = 0
    for i in range(0, len(hist_daily_bars)):
        if hist_daily_bars[i].date == date:
            day_index = i
            break
    if day_index > 0:
        return round((hist_daily_bars[day_index].open - hist_daily_bars[day_index - 1].close) / hist_daily_bars[day_index - 1].close * 100, 2)
    return 0.0


def get_algo_type_texts():
    tags = get_algo_type_tags()
    descs = get_algo_type_descs()
    texts = []
    # tags, descs should have same length
    for i in range(0, len(tags)):
        texts.append({
            "tag": tags[i],
            "desc": descs[i],
        })
    return texts


def get_algo_type_descs():
    description = enums.AlgorithmType.todesc(enums.AlgorithmType.DAY_MOMENTUM)
    settings = TradingSettings.objects.first()
    if settings:
        description = enums.AlgorithmType.todesc(settings.algo_type)
    return description.split(" / ")


def get_algo_type_tags():
    tag = enums.AlgorithmType.totag(enums.AlgorithmType.DAY_MOMENTUM)
    settings = TradingSettings.objects.first()
    if settings:
        tag = enums.AlgorithmType.totag(settings.algo_type)
    return tag.split(" / ")


# utils for render UI

def get_account_type_for_render():
    if check_paper():
        account_type = {
            "value": "PAPER",
            "value_style": "bg-warning",
        }
    else:
        account_type = {
            "value": "LIVE",
            "value_style": "bg-success",
        }
    return account_type


def get_color_bar_chart_item_for_render(value):
    if value >= 0:
        return {
            'value': value,
            'itemStyle': {'color': config.PROFIT_COLOR},
        }
    return {
        'value': value,
        'itemStyle': {'color': config.LOSS_COLOR},
    }


def get_color_price_style_for_render(value):
    price = "+${}".format(value)
    price_style = "text-success"
    if value < 0:
        price = "-${}".format(abs(value))
        price_style = "text-danger"
    return (price, price_style)


def get_color_percentage_style_for_render(value):
    percentage = "+{}%".format(value)
    percentage_style = "text-success"
    if value < 0:
        percentage = "{}%".format(value)
        percentage_style = "text-danger"
    return (percentage, percentage_style)


def get_color_percentage_badge_style_for_render(value):
    percentage = "+{}%".format(value)
    percentage_style = "badge-soft-success"
    if value < 0:
        percentage = "{}%".format(value)
        percentage_style = "badge-soft-danger"
    return (percentage, percentage_style)


def get_net_profit_loss_for_render(acc_stat):
    day_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "day_pl_rate": "0.0%",
        "day_pl_rate_style": "badge-soft-dark",
    }
    if acc_stat:
        day_profit_loss["value"] = "${}".format(
            abs(acc_stat.day_profit_loss))
        day_pl_rate = acc_stat.day_profit_loss / \
            (acc_stat.net_liquidation - acc_stat.day_profit_loss)
        day_profit_loss["day_pl_rate"] = "{}%".format(
            round(day_pl_rate * 100, 2))
        if acc_stat.day_profit_loss > 0:
            day_profit_loss["value"] = "+" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-success"
            day_profit_loss["day_pl_rate"] = "+" + \
                day_profit_loss["day_pl_rate"]
            day_profit_loss["day_pl_rate_style"] = "badge-soft-success"
        elif acc_stat.day_profit_loss < 0:
            day_profit_loss["value"] = "-" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-danger"
            day_profit_loss["day_pl_rate_style"] = "badge-soft-danger"
    return day_profit_loss


def get_day_profit_loss_for_render(perf):
    day_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "day_pl_rate": "0.0%",
        "day_pl_rate_style": "badge-soft-dark",
    }
    if perf:
        day_profit_loss["value"] = "${}".format(
            abs(perf.day_profit_loss))
        day_pl_rate = 0.0
        if perf.total_buy_amount > 0:
            day_pl_rate = (perf.total_sell_amount -
                           perf.total_buy_amount) / perf.total_buy_amount
        day_profit_loss["day_pl_rate"] = "{}%".format(
            round(day_pl_rate * 100, 2))
        if perf.day_profit_loss > 0:
            day_profit_loss["value"] = "+" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-success"
            day_profit_loss["day_pl_rate"] = "+" + \
                day_profit_loss["day_pl_rate"]
            day_profit_loss["day_pl_rate_style"] = "badge-soft-success"
        elif perf.day_profit_loss < 0:
            day_profit_loss["value"] = "-" + day_profit_loss["value"]
            day_profit_loss["value_style"] = "text-danger"
            day_profit_loss["day_pl_rate_style"] = "badge-soft-danger"
    return day_profit_loss


def get_swing_profit_loss_for_render(trades):
    swing_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "swing_pl_rate": "0.0%",
        "swing_pl_rate_style": "badge-soft-dark",
        "swing_win_rate": "0.0%",
        "swing_pl_ratio": "1.0",
    }
    total_cost = 0.0
    total_sold = 0.0
    win_count = 0
    loss_count = 0
    total_profit = 0.0
    total_loss = 0.0
    for trade in trades:
        total_cost += trade.buy_price * trade.quantity
        total_sold += trade.sell_price * trade.quantity
        if trade.sell_price > trade.buy_price:
            win_count += 1
            total_profit += (trade.sell_price -
                             trade.buy_price) * trade.quantity
        if trade.sell_price < trade.buy_price:
            loss_count += 1
            total_loss += (trade.buy_price - trade.sell_price) * trade.quantity
    if len(trades) > 0:
        swing_profit_loss["swing_win_rate"] = "{}%".format(
            round(win_count / len(trades) * 100, 2))
    avg_profit = 0.0
    if win_count > 0:
        avg_profit = total_profit / win_count
    avg_loss = 0.0
    if loss_count > 0:
        avg_loss = total_loss / loss_count
    if avg_loss > 0:
        swing_profit_loss["swing_pl_ratio"] = round(avg_profit/avg_loss)
    profit_loss = total_sold - total_cost
    profit_loss_rate = 0.0
    if total_cost > 0:
        profit_loss_rate = (total_sold - total_cost) / total_cost
    swing_profit_loss["value"] = "${}".format(abs(round(profit_loss, 2)))
    swing_profit_loss["swing_pl_rate"] = "{}%".format(
        round(profit_loss_rate * 100, 2))
    if profit_loss > 0:
        swing_profit_loss["value"] = "+" + swing_profit_loss["value"]
        swing_profit_loss["value_style"] = "text-success"
        swing_profit_loss["swing_pl_rate"] = "+" + \
            swing_profit_loss["swing_pl_rate"]
        swing_profit_loss["swing_pl_rate_style"] = "badge-soft-success"
    elif profit_loss < 0:
        swing_profit_loss["value"] = "-" + swing_profit_loss["value"]
        swing_profit_loss["value_style"] = "text-danger"
        swing_profit_loss["swing_pl_rate_style"] = "badge-soft-danger"
    return swing_profit_loss


def get_minute_candle_data_for_render(bars):
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
        "vwaps": [],
        "ema9s": [],
    }
    for timestamp, candle in bars.iterrows():
        candle_data['times'].append(local_time_minute(timestamp))
        # open, close, low, high
        candle_data['candles'].append(
            [candle['open'], candle['close'], candle['low'], candle['high']])
        if candle['close'] < candle['open']:
            candle_data['volumes'].append({
                'value': candle['volume'],
                'itemStyle': {'color': config.LOSS_COLOR},
            })
        else:
            candle_data['volumes'].append({
                'value': candle['volume'],
                'itemStyle': {'color': config.PROFIT_COLOR},
            })
        candle_data['vwaps'].append(candle['vwap'])
        candle_data['ema9s'].append(round(candle['ema9'], 2))
    return candle_data


def get_last_60d_daily_candle_data_for_render(symbol, date):
    daily_bars = HistoricalDailyBar.objects.filter(symbol=symbol)
    end_idx = -1
    for i in range(0, len(daily_bars)):
        if daily_bars[i].date == date:
            end_idx = i + 1
            break
    start_idx = max(end_idx - 60, 0)
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
    }
    for i in range(start_idx, end_idx):
        candle = daily_bars[i]
        candle_data["times"].append(candle.date.strftime("%m/%d"))
        # open, close, low, high
        candle_data["candles"].append(
            [candle.open, candle.close, candle.low, candle.high])
        if candle.close < candle.open:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.LOSS_COLOR},
            })
        else:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.PROFIT_COLOR},
            })
    return candle_data


def get_swing_daily_candle_data_for_render(symbol):
    daily_bars = SwingHistoricalDailyBar.objects.filter(symbol=symbol)
    candle_data = {
        "times": [],
        "candles": [],
        "volumes": [],
        "rsi_10": [],
        "sma_55": [],
        "sma_120": [],
    }
    for i in range(0, len(daily_bars)):
        candle = daily_bars[i]
        candle_data["times"].append(candle.date.strftime("%Y/%m/%d"))
        # open, close, low, high
        candle_data["candles"].append(
            [candle.open, candle.close, candle.low, candle.high])
        if candle.close < candle.open:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.LOSS_COLOR},
            })
        else:
            candle_data['volumes'].append({
                'value': candle.volume,
                'itemStyle': {'color': config.PROFIT_COLOR},
            })
        candle_data["rsi_10"].append(round(candle.rsi_10, 2))
        candle_data["sma_55"].append(round(candle.sma_55, 2))
        candle_data["sma_120"].append(round(candle.sma_120, 2))
    return candle_data


def get_day_trade_stat_record_for_render(symbol, trade_stat, date):
    key_statistics = get_hist_key_stat(symbol, date)
    mktcap = 0
    short_float = None
    float_shares = 0
    turnover_rate = "0.0%"
    relative_volume = 0
    if key_statistics:
        mktcap = millify(key_statistics.market_value)
        if key_statistics.short_float:
            short_float = "{}%".format(key_statistics.short_float)
        float_shares = millify(key_statistics.outstanding_shares)
        if key_statistics.turnover_rate:
            turnover_rate = "{}%".format(
                round(key_statistics.turnover_rate * 100, 2))
        else:
            turnover_rate = None
        relative_volume = round(
            key_statistics.volume / key_statistics.avg_vol_3m, 2)
    win_rate = "0.0%"
    if trade_stat["trades"] > 0:
        win_rate = "{}%".format(
            round(trade_stat["win_trades"] / trade_stat["trades"] * 100, 2))
    avg_profit = 0.0
    if trade_stat["win_trades"] > 0:
        avg_profit = trade_stat["total_gain"] / trade_stat["win_trades"]
    avg_loss = 0.0
    if trade_stat["loss_trades"] > 0:
        avg_loss = abs(trade_stat["total_loss"] / trade_stat["loss_trades"])
    profit_loss_ratio = 1.0
    if avg_loss > 0:
        profit_loss_ratio = round(avg_profit/avg_loss, 2)
    avg_price = "${}".format(
        round(trade_stat["total_cost"] / trade_stat["trades"], 2))
    profit_loss = "+${}".format(round(trade_stat["profit_loss"], 2))
    profit_loss_style = "text-success"
    if trade_stat["profit_loss"] < 0:
        profit_loss = "-${}".format(abs(round(trade_stat["profit_loss"], 2)))
        profit_loss_style = "text-danger"
    gap_value = get_gap_by_symbol_date(symbol, key_statistics.date)
    gap = "0.0%"
    if gap_value > 0:
        gap = "+{}%".format(gap_value)
    else:
        gap = "{}%".format(gap_value)

    webull_news = WebullNews.objects.filter(
        symbol=symbol).filter(date=date)
    news_count = 0
    for webull_new in webull_news:
        news_time = webull_new.news_time.split('.')[0]
        if datetime.strptime(news_time, "%Y-%m-%dT%H:%M:%S").date() == key_statistics.date:
            news_count += 1

    return {
        "symbol": symbol,
        "trades": trade_stat["trades"],
        "profit_loss_value": round(trade_stat["profit_loss"], 2),
        "profit_loss": profit_loss,
        "win_rate": win_rate,
        "profit_loss_ratio": profit_loss_ratio,
        "avg_price": avg_price,
        "profit_loss_style": profit_loss_style,
        "short_float": short_float,
        "float_shares": float_shares,
        "relative_volume": relative_volume,
        "gap": gap,
        "news": news_count,
        "mktcap": mktcap,
        "turnover_rate": turnover_rate,
        "top_gain": "+${}".format(trade_stat["top_gain"]),
        "top_loss": "-${}".format(abs(trade_stat["top_loss"])),
    }


def get_swing_trade_stat_record_for_render(symbol, trade_stat):
    win_rate = "0.0%"
    if trade_stat["trades"] > 0:
        win_rate = "{}%".format(
            round(trade_stat["win_trades"] / trade_stat["trades"] * 100, 2))
    avg_profit = 0.0
    if trade_stat["win_trades"] > 0:
        avg_profit = trade_stat["total_gain"] / trade_stat["win_trades"]
    avg_loss = 0.0
    if trade_stat["loss_trades"] > 0:
        avg_loss = abs(trade_stat["total_loss"] / trade_stat["loss_trades"])
    profit_loss_ratio = 1.0
    if avg_loss > 0:
        profit_loss_ratio = round(avg_profit/avg_loss, 2)
    avg_cost = "${}".format(
        round(trade_stat["total_cost"] / trade_stat["trades"], 2))
    avg_sold = "${}".format(
        round(trade_stat["total_sold"] / trade_stat["trades"], 2))
    profit_loss = "+${}".format(round(trade_stat["profit_loss"], 2))
    profit_loss_style = "text-success"
    if trade_stat["profit_loss"] < 0:
        profit_loss = "-${}".format(abs(round(trade_stat["profit_loss"], 2)))
        profit_loss_style = "text-danger"
    profit_loss_percent_value = (
        trade_stat["total_sold"] - trade_stat["total_cost"]) / trade_stat["total_cost"]
    profit_loss_percent = "+{}%".format(
        round(profit_loss_percent_value * 100, 2))
    if profit_loss_percent_value < 0:
        profit_loss_percent = "{}%".format(
            round(profit_loss_percent_value * 100, 2))

    return {
        "symbol": symbol,
        "trades": trade_stat["trades"],
        "profit_loss_value": round(trade_stat["profit_loss"], 2),
        "profit_loss": profit_loss,
        "profit_loss_percent": profit_loss_percent,
        "win_rate": win_rate,
        "profit_loss_ratio": profit_loss_ratio,
        "avg_cost": avg_cost,
        "avg_sold": avg_sold,
        "profit_loss_style": profit_loss_style,
        "total_cost": round(trade_stat["total_cost"], 2),
        "total_sold": round(trade_stat["total_sold"], 2),
        "top_gain": "+${}".format(trade_stat["top_gain"]),
        "top_loss": "-${}".format(abs(trade_stat["top_loss"])),
    }


def get_value_stat_from_trades_for_render(day_trades, field_name, value_idx_func, value_labels):
    statistics_list = get_stats_empty_list(size=len(value_labels))
    # for P&L, win rate and profit/loss ratio, trades by value
    for day_trade in day_trades:
        symbol = day_trade['symbol']
        buy_date = day_trade['buy_time'].date()
        key_statistics = get_hist_key_stat(symbol, buy_date)
        if key_statistics:
            value = getattr(key_statistics, field_name)
            value_idx = value_idx_func(value)
            if 'sell_price' in day_trade:
                gain = (day_trade['sell_price'] -
                        day_trade['buy_price']) * day_trade['quantity']
                if gain > 0:
                    statistics_list[value_idx]['win_trades'] += 1
                    statistics_list[value_idx]['total_profit'] += gain
                else:
                    statistics_list[value_idx]['loss_trades'] += 1
                    statistics_list[value_idx]['total_loss'] += gain
                statistics_list[value_idx]['profit_loss'] += gain
                statistics_list[value_idx]['trades'] += 1
    value_profit_loss = []
    value_win_rate = []
    value_profit_loss_ratio = []
    value_trades = []
    # calculate win rate and profit/loss ratio
    for stat in statistics_list:
        value_trades.append(stat['trades'])
        value_profit_loss.append(get_color_bar_chart_item_for_render(
            round(stat['profit_loss'], 2)))
        if stat['trades'] > 0:
            value_win_rate.append(
                round(stat['win_trades']/stat['trades'] * 100, 2))
        else:
            value_win_rate.append(0.0)
        avg_profit = 1.0
        if stat['win_trades'] > 0:
            avg_profit = stat['total_profit'] / \
                stat['win_trades']
        avg_loss = 1.0
        if stat['loss_trades'] > 0:
            avg_loss = stat['total_loss'] / stat['loss_trades']
        profit_loss_ratio = 0.0
        if stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        value_profit_loss_ratio.append(profit_loss_ratio)

    return {
        "profit_loss": value_profit_loss,
        "win_rate": value_win_rate,
        "profit_loss_ratio": value_profit_loss_ratio,
        "trades": value_trades,
    }


def get_hourly_stat_from_trades_for_render(day_trades):
    hourly_statistics = get_stats_empty_list(size=32)
    # for hourly P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        hourly_idx = get_market_hourly_interval_index(
            local_datetime(day_trade['buy_time']))
        if 'sell_price' in day_trade:
            gain = (day_trade['sell_price'] -
                    day_trade['buy_price']) * day_trade['quantity']
            if gain > 0:
                hourly_statistics[hourly_idx]['win_trades'] += 1
                hourly_statistics[hourly_idx]['total_profit'] += gain
            else:
                hourly_statistics[hourly_idx]['loss_trades'] += 1
                hourly_statistics[hourly_idx]['total_loss'] += gain
            hourly_statistics[hourly_idx]['profit_loss'] += gain
            hourly_statistics[hourly_idx]['trades'] += 1
    hourly_profit_loss = []
    hourly_win_rate = []
    hourly_profit_loss_ratio = []
    hourly_trades = []
    # calculate win rate and profit/loss ratio
    for hourly_stat in hourly_statistics:
        hourly_trades.append(hourly_stat['trades'])
        hourly_profit_loss.append(get_color_bar_chart_item_for_render(
            round(hourly_stat['profit_loss'], 2)))
        if hourly_stat['trades'] > 0:
            hourly_win_rate.append(
                round(hourly_stat['win_trades']/hourly_stat['trades'] * 100, 2))
        else:
            hourly_win_rate.append(0.0)
        avg_profit = 1.0
        if hourly_stat['win_trades'] > 0:
            avg_profit = hourly_stat['total_profit'] / \
                hourly_stat['win_trades']
        avg_loss = 1.0
        if hourly_stat['loss_trades'] > 0:
            avg_loss = hourly_stat['total_loss'] / hourly_stat['loss_trades']
        profit_loss_ratio = 0.0
        if hourly_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if hourly_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        hourly_profit_loss_ratio.append(profit_loss_ratio)

    return {
        "profit_loss": hourly_profit_loss,
        "win_rate": hourly_win_rate,
        "profit_loss_ratio": hourly_profit_loss_ratio,
        "trades": hourly_trades,
    }


def get_minutes_trade_marker_from_orders_for_render(orders, candles, time_scale, color):
    trade_price_records = []
    trade_quantity_records = []

    for order in orders:
        coord = [
            local_time_minute_scale(order.filled_time, time_scale),
            # use high price avoid block candle
            get_minute_candle_high_by_time_minute(
                candles, local_time_minute_scale(order.filled_time, time_scale)) + 0.01,
        ]
        trade_price_records.append({
            "name": "{}".format(order.avg_price),
            "coord": coord,
            "value": order.avg_price,
            "itemStyle": {"color": color},
            "label": {"fontSize": 10},
        })
        trade_quantity_records.append({
            "name": "+{}".format(order.filled_quantity),
            "coord": coord,
            "value": order.filled_quantity,
            "itemStyle": {"color": color},
            "label": {"fontSize": 10},
        })

    return (trade_price_records, trade_quantity_records)


def get_daily_trade_marker_from_trades_for_render(trades):
    trade_price_records = []
    trade_quantity_records = []

    for trade in trades:
        symbol = trade.symbol
        buy_date = trade.buy_date
        coord = [
            buy_date.strftime("%Y/%m/%d"),
            # use high price avoid block candle
            get_swing_daily_candle_high_by_date(symbol, buy_date) + 0.01,
        ]
        trade_price_records.append({
            "name": "{}".format(trade.buy_price),
            "coord": coord,
            "value": trade.buy_price,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
        trade_quantity_records.append({
            "name": "+{}".format(trade.quantity),
            "coord": coord,
            "value": trade.quantity,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
        sell_date = trade.sell_date
        coord = [
            sell_date.strftime("%Y/%m/%d"),
            # use high price avoid block candle
            get_swing_daily_candle_high_by_date(symbol, sell_date) + 0.01,
        ]
        trade_price_records.append({
            "name": "{}".format(trade.sell_price),
            "coord": coord,
            "value": trade.sell_price,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })
        trade_quantity_records.append({
            "name": "-{}".format(trade.quantity),
            "coord": coord,
            "value": trade.quantity,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })

    return (trade_price_records, trade_quantity_records)
