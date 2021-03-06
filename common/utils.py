import pytz
import math
import pandas as pd
import numpy as np
from typing import List, Optional
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import datetime
from common import db, config, enums, constants
from sdk import fmpsdk
from webull_trader.models import HistoricalMinuteBar, StockQuote, SwingHistoricalDailyBar, TradingSettings, WebullNews, WebullOrder, HistoricalDailyBar


def get_attr(obj: dict, key: str) -> str:
    if obj and key in obj:
        return obj[key]
    return ''


def get_attr_to_num(obj: dict, key: str) -> int:
    if obj and key in obj:
        try:
            return int(obj[key])
        except:
            pass
    return 0


def get_attr_to_float(obj: dict, key: str) -> float:
    if obj and key in obj:
        try:
            return float(obj[key])
        except:
            pass
    return 0.0


def get_attr_to_float_or_none(obj: dict, key: str) -> Optional[float]:
    if obj and key in obj:
        try:
            return float(obj[key])
        except:
            pass
    return None


MILLNAMES = ['', 'K', 'M', 'B', 'T']


def millify(n: float) -> str:
    if not n:
        return n
    millidx = max(0, min(len(MILLNAMES)-1,
                         int(math.floor(0 if n == 0 else math.log10(abs(n))/3))))
    return '{:.2f}{}'.format(n / 10**(3 * millidx), MILLNAMES[millidx])


def local_datetime(t: datetime) -> datetime:
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    return localtz


def local_time_minute(t: datetime) -> str:
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M'
    return localtz.strftime(format)


def local_time_minute_second(t: datetime) -> str:
    utc = t.replace(tzinfo=pytz.UTC)
    localtz = utc.astimezone(timezone.get_current_timezone())
    format = '%H:%M:%S'
    return localtz.strftime(format)


# hack to delay 1 minute
def local_time_minute_delay(t: datetime) -> str:
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
def local_time_minute_scale(t: datetime, time_scale: int) -> str:
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


def get_now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _open_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return series[0]
    return 0


def _close_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return series[-1]
    return 0


def _high_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return np.max(series)
    return 0


def _low_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return np.min(series)
    return 0


def _volume_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return np.sum(series)
    return 0


def _vwap_resampler(series: pd.Series) -> float:
    if series.size > 0:
        return series[-1]
    return 0


def convert_2m_bars(bars: pd.DataFrame) -> pd.DataFrame:
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


def convert_5m_bars(bars: pd.DataFrame) -> pd.DataFrame:
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


def is_market_hour() -> bool:
    return is_regular_market_hour() or is_extended_market_hour()


def is_extended_market_hour() -> bool:
    return is_pre_market_hour() or is_after_market_hour()


def is_pre_market_hour() -> bool:
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


def is_pre_market_hour_15m() -> bool:
    """
    NY pre market hour from 04:00 to 04:15
    """
    now = datetime.now()
    if now.hour < 4 or now.hour > 4:
        return False
    # first 15 minutes
    if now.hour == 4 and now.minute > 15:
        return False
    return True


def is_pre_market_hour_now() -> bool:
    """
    NY pre market hour from 04:00 to 09:30
    """
    now = datetime.now()
    if now.hour < 4 or now.hour > 9:
        return False
    if now.hour == 9 and now.minute >= 30:
        return False
    return True


def is_after_market_hour() -> bool:
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


def is_after_market_hour_15m() -> bool:
    """
    NY after market hour from 16:00 to 16:15
    """
    now = datetime.now()
    if now.hour < 16 or now.hour > 16:
        return False
    # first 15 minutes
    if now.hour == 16 and now.minute > 15:
        return False
    return True


def is_after_market_hour_now() -> bool:
    """
    NY after market hour from 16:00 to 20:00
    """
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    return True


def is_regular_market_hour() -> bool:
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


def is_regular_market_hour_15m() -> bool:
    """
    NY regular market hour from 09:30 to 09:45
    """
    now = datetime.now()
    if now.hour < 9 or now.hour > 9:
        return False
    if now.minute < 30 or now.minute > 45:
        return False
    return True


def is_regular_market_hour_now() -> bool:
    """
    NY regular market hour from 09:30 to 16:00
    """
    now = datetime.now()
    if now.hour < 9 or now.hour >= 16:
        return False
    if now.hour == 9 and now.minute < 30:
        return False
    return True


def is_pre_market_time(t: datetime) -> bool:
    if t.hour < 4 or t.hour > 9:
        return False
    if t.hour == 9 and t.minute >= 30:
        return False
    return True


def is_after_market_time(t: datetime) -> bool:
    if t.hour < 16 or t.hour >= 20:
        return False
    return True


def is_regular_market_time(t: datetime) -> bool:
    if t.hour < 9 or t.hour >= 16:
        return False
    if t.hour == 9 and t.minute < 30:
        return False
    return True


def is_trading_hour_end(trading_hour: enums.TradingHourType) -> bool:
    """
    check if trading end based on TradingHourType (2 minutes early)
    """
    now = datetime.now()
    if trading_hour == enums.TradingHourType.BEFORE_MARKET_OPEN:
        if now.hour > 9 or (now.hour == 9 and now.minute >= 28):
            return True
    elif trading_hour == enums.TradingHourType.REGULAR:
        if now.hour >= 16 or (now.hour == 15 and now.minute >= 58):
            return True
    elif trading_hour == enums.TradingHourType.AFTER_MARKET_CLOSE:
        if now.hour >= 20 or (now.hour == 19 and now.minute >= 58):
            return True
    return False


def get_trading_hour() -> Optional[enums.TradingHourType]:
    if is_pre_market_hour_now():
        return enums.TradingHourType.BEFORE_MARKET_OPEN
    elif is_after_market_hour_now():
        return enums.TradingHourType.AFTER_MARKET_CLOSE
    elif is_regular_market_hour_now():
        return enums.TradingHourType.REGULAR
    return None


def calculate_charts_ema9(charts: List[dict]) -> List[dict]:
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


def get_quote_sector(quote: Optional[StockQuote] = None) -> str:
    if quote:
        if quote.is_etf:
            return "ETF"
        return quote.sector
    return ""


def get_swing_avg_true_range(symbol: str, period: int = 20) -> float:
    daily_bars = SwingHistoricalDailyBar.objects.filter(
        symbol=symbol).order_by('-id')[:(period + 1)][::-1]
    true_range_list = []
    for i in range(1, len(daily_bars)):
        prev_bar = daily_bars[i - 1]
        current_bar = daily_bars[i]
        true_range = max(current_bar.high - current_bar.low, current_bar.high -
                         prev_bar.close, prev_bar.close - current_bar.low)
        true_range_list.append(true_range)
    N = sum(true_range_list)/len(true_range_list)
    return N


def get_day_avg_true_range(bars: pd.DataFrame, period: int = 10) -> float:
    period_bars = bars.head(len(bars) - 1).tail(period + 1)
    true_range_list = []
    for i in range(0, len(period_bars) - 1):
        current_bar = period_bars.iloc[len(period_bars) - i - 1]
        prev_bar = period_bars.iloc[len(period_bars) - i - 2]
        true_range = max(current_bar['high'] - current_bar['low'], current_bar['high'] -
                         prev_bar['close'], prev_bar['close'] - current_bar['low'])
        true_range_list.append(true_range)
    N = sum(true_range_list)/len(true_range_list)
    return N


def is_paper_trading():
    settings = TradingSettings.objects.first()
    if not settings:
        print(
            "[{}] Cannot find trading settings, default paper trading!".format(get_now()))
        return True
    return settings.paper


def get_algo_type() -> enums.AlgorithmType:
    settings = TradingSettings.objects.first()
    if settings == None:
        print("[{}] Cannot find trading settings, default algo type!".format(get_now()))
        return enums.AlgorithmType.DAY_MOMENTUM
    return settings.algo_type


def get_order_id_from_response(order_response: dict, paper: bool = True) -> Optional[str]:
    if paper:
        if 'orderId' in order_response:
            order_id = order_response['orderId']
            return str(order_id)
    else:
        if 'data' in order_response and 'orderId' in order_response['data']:
            order_id = order_response['data']['orderId']
            return str(order_id)
    return None


def get_avg_change_from_movers(movers) -> float:
    if len(movers) > 0:
        total_change = 0.0
        for mover in movers:
            total_change += mover['change_percentage']
        return round(total_change / len(movers), 2)
    return 0.0


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


def is_day_trade_setup(setup: enums.SetupType) -> bool:
    # include failed to sell order
    return setup < 100 or setup == enums.SetupType.ERROR_FAILED_TO_SELL


def is_day_trade_algo(algo: enums.AlgorithmType) -> bool:
    return algo < 100 or (algo >= 200 and algo < 300)


def is_swing_trade_algo(algo: enums.AlgorithmType) -> bool:
    return algo >= 100 and algo < 300


def check_require_top_list_algo(algo):
    if algo == enums.AlgorithmType.DAY_RED_TO_GREEN:
        return True
    return False


def get_day_trade_orders(date=None, symbol=None):
    # only limit orders for day trades
    # TODO, also include partial filled
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
        if is_day_trade_setup(order.setup):
            buy_orders.append(order)
    sell_orders = []
    for order in lmt_sell_orders:
        if is_day_trade_setup(order.setup):
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
            "setup": buy_order.setup,
            "buy_order": buy_order,
        })
    for sell_order in sell_orders:
        # fill sell side
        for trade in trades:
            if sell_order.symbol == trade["symbol"] and sell_order.filled_quantity == trade["quantity"] and "sell_price" not in trade:
                trade["sell_price"] = sell_order.avg_price
                trade["sell_time"] = sell_order.filled_time
                trade["sell_order_id"] = sell_order.order_id
                trade["sell_order"] = sell_order
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
        "50M-100M (Micro Cap)",  # 1
        "100M-150M (Micro Cap)",  # 2
        "150M-200M (Micro Cap)",  # 3
        "200M-250M (Micro Cap)",  # 4
        "250M-300M (Micro Cap)",  # 5
        "300M-400M (Small Cap)",  # 6
        "400M-500M (Small Cap)",  # 7
        "500M-600M (Small Cap)",  # 8
        "600M-700M (Small Cap)",  # 9
        "700M-800M (Small Cap)",  # 10
        "800M-900M (Small Cap)",  # 11
        "900M-1B (Small Cap)",  # 12
        "1B-2B (Small Cap)",  # 13
        "2B-10B (Mid Cap)",  # 14
        "10B-200B (Large Cap)",  # 15
        "200B+ (Mega Cap)",  # 16
    ]


def get_market_cap_range_index(mktcap):
    index = -1
    if mktcap <= 50000000:
        index = 0
    elif mktcap <= 100000000:
        index = 1
    elif mktcap <= 150000000:
        index = 2
    elif mktcap <= 200000000:
        index = 3
    elif mktcap <= 250000000:
        index = 4
    elif mktcap <= 300000000:
        index = 5
    elif mktcap <= 400000000:
        index = 6
    elif mktcap <= 500000000:
        index = 7
    elif mktcap <= 600000000:
        index = 8
    elif mktcap <= 700000000:
        index = 9
    elif mktcap <= 800000000:
        index = 10
    elif mktcap <= 900000000:
        index = 11
    elif mktcap <= 1000000000:
        index = 12
    elif mktcap <= 2000000000:
        index = 13
    elif mktcap <= 10000000000:
        index = 14
    elif mktcap <= 200000000000:
        index = 15
    else:
        index = 16
    return index


def get_free_float_range_labels():
    return [
        "None",  # 0
        "0-1M",  # 1
        "1M-2M",  # 2
        "2M-3M",  # 3
        "3M-4M",  # 4
        "4M-5M",  # 5
        "5M-6M",  # 6
        "6M-7M",  # 7
        "7M-8M",  # 8
        "8M-9M",  # 9
        "9M-10M",  # 10
        "10M-11M",  # 11
        "11M-12M",  # 12
        "12M-13M",  # 13
        "13M-14M",  # 14
        "14M-15M",  # 15
        "15M-16M",  # 16
        "16M-17M",  # 17
        "17M-18M",  # 18
        "18M-19M",  # 19
        "19M-20M",  # 20
        "20M-30M",  # 21
        "30M-50M",  # 22
        "50M-100M",  # 23
        "100M-200M",  # 24
        "200M-500M",  # 25
        "500M-1B",  # 26
        "1B+",  # 27
    ]


def get_free_float_range_index(free_float):
    index = -1
    if free_float == None:
        index = 0
    elif free_float <= 1000000:
        index = 1
    elif free_float <= 2000000:
        index = 2
    elif free_float <= 3000000:
        index = 3
    elif free_float <= 4000000:
        index = 4
    elif free_float <= 5000000:
        index = 5
    elif free_float <= 6000000:
        index = 6
    elif free_float <= 7000000:
        index = 7
    elif free_float <= 8000000:
        index = 8
    elif free_float <= 9000000:
        index = 9
    elif free_float <= 10000000:
        index = 10
    elif free_float <= 11000000:
        index = 11
    elif free_float <= 12000000:
        index = 12
    elif free_float <= 13000000:
        index = 13
    elif free_float <= 14000000:
        index = 14
    elif free_float <= 15000000:
        index = 15
    elif free_float <= 16000000:
        index = 16
    elif free_float <= 17000000:
        index = 17
    elif free_float <= 18000000:
        index = 18
    elif free_float <= 19000000:
        index = 19
    elif free_float <= 20000000:
        index = 20
    elif free_float <= 30000000:
        index = 21
    elif free_float <= 50000000:
        index = 22
    elif free_float <= 100000000:
        index = 23
    elif free_float <= 200000000:
        index = 24
    elif free_float <= 500000000:
        index = 25
    elif free_float <= 1000000000:
        index = 26
    else:
        index = 27
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
        "0-1m",  # 0
        "1-3m",  # 1
        "3-5m",  # 2
        "5-10m",  # 3
        "10-15m",  # 4
        "15-20m",  # 5
        "20-25m",  # 6
        "25-30m",  # 7
        "30-35m",  # 8
        "35-40m",  # 9
        "40-45m",  # 10
        "45-50m",  # 11
        "50-55m",  # 12
        "55-60m",  # 13
        "60m+",  # 14
    ]


def get_holding_time_index(holding_sec):
    index = -1
    if holding_sec <= 60:
        index = 0
    elif holding_sec <= 180:
        index = 1
    elif holding_sec <= 300:
        index = 2
    elif holding_sec <= 600:
        index = 3
    elif holding_sec <= 900:
        index = 4
    elif holding_sec <= 1200:
        index = 5
    elif holding_sec <= 1500:
        index = 6
    elif holding_sec <= 1800:
        index = 7
    elif holding_sec <= 2100:
        index = 8
    elif holding_sec <= 2400:
        index = 9
    elif holding_sec <= 2700:
        index = 10
    elif holding_sec <= 3000:
        index = 11
    elif holding_sec <= 3300:
        index = 12
    elif holding_sec <= 3600:
        index = 13
    else:
        index = 14
    return index


def get_plpct_range_labels():
    return [
        "-80~100%",  # 0
        "-60~80%",  # 1
        "-40~60%",  # 2
        "-20~40%",  # 3
        "-0~20%",  # 4
        "+0~20%",  # 5
        "+20~40%",  # 6
        "+40~60%",  # 7
        "+60~80%",  # 8
        "+80~100%",  # 9
        "+100~120%",  # 10
        "+120%+",  # 11
    ]


def get_plpct_range_index(percentage):
    index = -1
    if percentage <= -80:
        index = 0
    elif percentage <= -60:
        index = 1
    elif percentage <= -40:
        index = 2
    elif percentage <= -20:
        index = 3
    elif percentage <= 0:
        index = 4
    elif percentage <= 20:
        index = 5
    elif percentage <= 40:
        index = 6
    elif percentage <= 60:
        index = 7
    elif percentage <= 80:
        index = 8
    elif percentage <= 100:
        index = 9
    elif percentage <= 120:
        index = 10
    else:
        index = 11
    return index


def get_relative_volume_labels():
    return [
        "0-1",  # 0
        "1-2",  # 1
        "2-3",  # 2
        "3-5",  # 3
        "5-10",  # 4
        "10-15",  # 5
        "15-20",  # 6
        "20-30",  # 7
        "30-40",  # 8
        "40-60",  # 9
        "60-100",  # 10
        "100+"  # 11
    ]


def get_relative_volume_index(rel_vol):
    index = -1
    if rel_vol <= 1:
        index = 0
    elif rel_vol <= 2:
        index = 1
    elif rel_vol <= 3:
        index = 2
    elif rel_vol <= 5:
        index = 3
    elif rel_vol <= 10:
        index = 4
    elif rel_vol <= 15:
        index = 5
    elif rel_vol <= 20:
        index = 6
    elif rel_vol <= 30:
        index = 7
    elif rel_vol <= 40:
        index = 8
    elif rel_vol <= 60:
        index = 9
    elif rel_vol <= 100:
        index = 10
    else:
        index = 11
    return index


def get_volume_labels():
    return [
        "None",  # 0
        "0-20K",  # 1
        "20-50K",  # 2
        "50-100K",  # 3
        "100-200K",  # 4
        "200-500K",  # 5
        "0.5-1M",  # 6
        "1M+",  # 7
    ]


def get_volume_index(vol):
    index = -1
    if vol == 0:
        index = 0
    elif vol <= 20000:
        index = 1
    elif vol <= 50000:
        index = 2
    elif vol <= 100000:
        index = 3
    elif vol <= 200000:
        index = 4
    elif vol <= 500000:
        index = 5
    elif vol <= 1000000:
        index = 6
    else:
        index = 7
    return index


def get_sector_labels() -> List[str]:
    return [
        constants.BASIC_MATERIALS,  # 0
        constants.COMMUNICATION_SERVICES,  # 1
        constants.CONSUMER_CYCLICAL,  # 2
        constants.CONSUMER_DEFENSIVE,  # 3
        constants.ENERGY,  # 4
        constants.FINANCIAL_SERVICES,  # 5
        constants.HEALTHCARE,  # 6
        constants.INDUSTRIALS,  # 7
        constants.REAL_ESTATE,  # 8
        constants.TECHNOLOGY,  # 9
        constants.UTILITIES,  # 10
        "None",  # 11
    ]


def get_sector_index(sector: str) -> int:
    index = -1
    if sector == constants.BASIC_MATERIALS:
        index = 0
    elif sector == constants.COMMUNICATION_SERVICES:
        index = 1
    elif sector == constants.CONSUMER_CYCLICAL:
        index = 2
    elif sector == constants.CONSUMER_DEFENSIVE:
        index = 3
    elif sector == constants.ENERGY:
        index = 4
    elif sector == constants.FINANCIAL_SERVICES:
        index = 5
    elif sector == constants.HEALTHCARE:
        index = 6
    elif sector == constants.INDUSTRIALS:
        index = 7
    elif sector == constants.REAL_ESTATE:
        index = 8
    elif sector == constants.TECHNOLOGY:
        index = 9
    elif sector == constants.UTILITIES:
        index = 10
    elif sector == None or sector == "":
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


def get_market_hourly_interval_index(t: datetime) -> int:
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


def get_minute_candle_low_by_time_minute(candle_data, time):
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
    return candle_data['candles'][idx][2]


def get_minute_candle_y_by_time_minute_action(candle_data, time, action):
    if action == enums.ActionType.BUY:
        return get_minute_candle_low_by_time_minute(candle_data, time) - 0.01
    else:
        return get_minute_candle_high_by_time_minute(candle_data, time) + 0.01


def get_trade_stat_dist_from_day_trades(day_trades):
    trades_dist = {}
    for trade in day_trades:
        symbol = trade.symbol
        gain = round(trade.total_sold - trade.total_cost, 2)
        # build trades_dist
        if symbol not in trades_dist:
            trades_dist[symbol] = {
                "trades": 0,
                "win_trades": 0,
                "loss_trades": 0,
                "total_gain": 0,
                "total_loss": 0,
                "profit_loss": 0,
                "sum_cost": 0,
                "top_gain": 0,
                "top_loss": 0,
            }
        trades_dist[symbol]["trades"] += 1
        trades_dist[symbol]["profit_loss"] += gain
        trades_dist[symbol]["sum_cost"] += (trade.total_cost / trade.quantity)
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
        total_cost = trade.total_cost
        total_sold = trade.total_sold
        gain = round(total_sold - total_cost, 2)
        quantity = trade.quantity
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
                "total_quantity": 0,
            }
        trades_dist[symbol]["trades"] += 1
        trades_dist[symbol]["profit_loss"] += gain
        trades_dist[symbol]["total_cost"] += total_cost
        trades_dist[symbol]["total_sold"] += total_sold
        trades_dist[symbol]["total_quantity"] += quantity
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


def get_swing_daily_candle_low_by_date(symbol, date):
    day_bar = SwingHistoricalDailyBar.objects.filter(
        symbol=symbol).filter(date=date).first()
    if day_bar:
        return day_bar.low
    return 0


def get_swing_daily_candle_y_by_date_action(symbol, date, action):
    if action == enums.ActionType.BUY:
        return get_swing_daily_candle_low_by_date(symbol, date) - 0.01
    else:
        return get_swing_daily_candle_high_by_date(symbol, date) + 0.01


def get_gap_by_symbol_date(symbol, date):
    if type(date) == str:
        date = datetime.strptime(date, '%Y-%m-%d').date()
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


def get_account_user_desc():
    account_type = "LIVE"
    account_email = ""
    if is_paper_trading():
        account_type = "PAPER"
    users = User.objects.all()
    for user in users:
        if user.is_staff:
            account_email = user.email
            break
    return "[{}] {}".format(account_type, account_email)


def get_minute_bars_df(minute_bars: HistoricalMinuteBar) -> pd.DataFrame:
    minute_bars = list(reversed(minute_bars))
    data_list = []
    for minute_bar in minute_bars:
        data_list.append([minute_bar.time.astimezone(timezone.get_current_timezone()), minute_bar.open,
                         minute_bar.high, minute_bar.low, minute_bar.close, minute_bar.volume, minute_bar.vwap])
    df = pd.DataFrame(data_list, columns=[
                      'timestamp', 'open', 'high', 'low', 'close', 'volume', 'vwap'])
    df.set_index('timestamp', inplace=True)
    return df


# utils for render UI

def get_account_type_for_render():
    if is_paper_trading():
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


def get_color_profit_loss_style_for_render(old_value, new_value):
    diff_value = round(new_value - old_value, 2)
    diff_percent = round((new_value - old_value) / old_value * 100, 2)
    profit_loss = "+${}".format(diff_value)
    profit_loss_percent = "+{}%".format(diff_percent)
    profit_loss_style = "text-success"
    if diff_value < 0:
        profit_loss = "-${}".format(abs(diff_value))
        profit_loss_percent = "{}%".format(diff_percent)
        profit_loss_style = "text-danger"
    return (profit_loss, profit_loss_percent, profit_loss_style)


def get_label_style_from_action(action):
    sign = "+"
    color = config.BUY_COLOR
    rotate = 180
    escape = "\n\n"
    if action == enums.ActionType.SELL:
        sign = "-"
        color = config.SELL_COLOR
        rotate = 0
        escape = ""
    return (color, sign, rotate, escape)


def get_net_profit_loss_for_render(acc_stat):
    day_profit_loss = {
        "value": "$0.0",
        "value_style": "",
        "day_pl_rate": "0.0%",
        "day_pl_rate_style": "badge-soft-dark",
    }
    if acc_stat and acc_stat.net_liquidation > 0:
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
    overall_total_cost = 0.0
    overall_total_sold = 0.0
    overall_win_count = 0
    overall_loss_count = 0
    overall_total_profit = 0.0
    overall_total_loss = 0.0
    for trade in trades:
        overall_total_cost += trade.total_cost
        overall_total_sold += trade.total_sold
        if trade.total_sold > trade.total_cost:
            overall_win_count += 1
            overall_total_profit += (trade.total_sold - trade.total_cost)
        if trade.total_sold < trade.total_cost:
            overall_loss_count += 1
            overall_total_loss += (trade.total_cost - trade.total_sold)
    if len(trades) > 0:
        swing_profit_loss["swing_win_rate"] = "{}%".format(
            round(overall_win_count / len(trades) * 100, 2))
    overall_avg_profit = 0.0
    if overall_win_count > 0:
        overall_avg_profit = overall_total_profit / overall_win_count
    overall_avg_loss = 0.0
    if overall_loss_count > 0:
        overall_avg_loss = overall_total_loss / overall_loss_count
    if overall_avg_loss > 0:
        swing_profit_loss["swing_pl_ratio"] = round(
            overall_avg_profit/overall_avg_loss, 2)
    profit_loss = overall_total_sold - overall_total_cost
    profit_loss_rate = 0.0
    if overall_total_cost > 0:
        profit_loss_rate = (overall_total_sold -
                            overall_total_cost) / overall_total_cost
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
    key_statistics = db.get_hist_key_stat(symbol, date)
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
        round(trade_stat["sum_cost"] / trade_stat["trades"], 2))
    profit_loss = "+${}".format(round(trade_stat["profit_loss"], 2))
    profit_loss_style = "text-success"
    if trade_stat["profit_loss"] < 0:
        profit_loss = "-${}".format(abs(round(trade_stat["profit_loss"], 2)))
        profit_loss_style = "text-danger"
    gap_value = get_gap_by_symbol_date(symbol, date)
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
        if datetime.strptime(news_time, "%Y-%m-%dT%H:%M:%S").date() == date:
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
        round(trade_stat["total_cost"] / trade_stat["total_quantity"], 2))
    avg_sold = "${}".format(
        round(trade_stat["total_sold"] / trade_stat["total_quantity"], 2))
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
        "total_cost": "${}".format(round(trade_stat["total_cost"], 2)),
        "total_sold": "${}".format(round(trade_stat["total_sold"], 2)),
        "top_gain": "+${}".format(trade_stat["top_gain"]),
        "top_loss": "-${}".format(abs(trade_stat["top_loss"])),
    }


def get_value_stat_from_trades_for_render(day_trades, field_name, value_idx_func, value_labels):
    statistics_list = get_stats_empty_list(size=len(value_labels))
    # for P&L, win rate and profit/loss ratio, trades by value
    for day_trade in day_trades:
        symbol = day_trade.symbol
        buy_date = day_trade.buy_date
        key_statistics = db.get_hist_key_stat(symbol, buy_date)
        if key_statistics:
            value = getattr(key_statistics, field_name)
            value_idx = value_idx_func(value)
            gain = day_trade.total_sold - day_trade.total_cost
            if gain > 0:
                statistics_list[value_idx]['win_trades'] += 1
                statistics_list[value_idx]['total_profit'] += gain
            else:
                statistics_list[value_idx]['loss_trades'] += 1
                statistics_list[value_idx]['total_loss'] += gain
            statistics_list[value_idx]['profit_loss'] += gain
            statistics_list[value_idx]['trades'] += 1
    value_profit_loss = []
    value_total_profit = []
    value_total_loss = []
    value_win_rate = []
    value_profit_loss_ratio = []
    value_trades = []
    # calculate win rate and profit/loss ratio
    for stat in statistics_list:
        value_trades.append(stat['trades'])
        value_profit_loss.append(get_color_bar_chart_item_for_render(
            round(stat['profit_loss'], 2)))
        value_total_profit.append(round(stat['total_profit'], 2))
        value_total_loss.append(round(stat['total_loss'], 2))
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
        "total_profit": value_total_profit,
        "total_loss": value_total_loss,
        "win_rate": value_win_rate,
        "profit_loss_ratio": value_profit_loss_ratio,
        "trades": value_trades,
    }


def get_hourly_stat_from_trades_for_render(day_trades):
    hourly_statistics = get_stats_empty_list(size=32)
    # for hourly P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        hourly_idx = get_market_hourly_interval_index(
            local_datetime(day_trade.buy_time))
        gain = day_trade.total_sold - day_trade.total_cost
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


def get_minutes_trade_marker_from_orders_for_render(orders, candles, time_scale):
    if len(candles['candles']) == 0:
        return ([], [])

    trade_price_records = []
    trade_quantity_records = []

    for order in orders:
        color, sign, rotate, escape = get_label_style_from_action(order.action)
        coord = [
            local_time_minute_scale(order.filled_time, time_scale),
            # use high price avoid block candle
            get_minute_candle_y_by_time_minute_action(
                candles, local_time_minute_scale(order.filled_time, time_scale), order.action),
        ]
        trade_price_records.append({
            "name": "{}{}".format(escape, order.avg_price),
            "coord": coord,
            "value": order.avg_price,
            "itemStyle": {"color": color, "rotate": rotate},
            "label": {"fontSize": 10},
        })
        trade_quantity_records.append({
            "name": "{}{}{}".format(escape, sign, order.filled_quantity),
            "coord": coord,
            "value": order.filled_quantity,
            "itemStyle": {"color": color, "rotate": rotate},
            "label": {"fontSize": 10},
        })

    return (trade_price_records, trade_quantity_records)


def get_daily_trade_marker_from_position_for_render(position):
    trade_price_records = []
    trade_quantity_records = []

    symbol = position.symbol
    orders = position.orders.all()
    for order in orders:
        filled_date = order.filled_time.date()
        filled_price = order.avg_price
        filled_quantity = order.filled_quantity
        coord = [
            filled_date.strftime("%Y/%m/%d"),
            # use high price avoid block candle
            get_swing_daily_candle_y_by_date_action(
                symbol, filled_date, order.action),
        ]
        color, sign, rotate, escape = get_label_style_from_action(order.action)
        trade_price_records.append({
            "name": "{}{}".format(escape, filled_price),
            "coord": coord,
            "value": filled_price,
            "itemStyle": {"color": color, "rotate": rotate},
            "label": {"fontSize": 10},
        })
        trade_quantity_records.append({
            "name": "{}{}{}".format(escape, sign, filled_quantity),
            "coord": coord,
            "value": filled_quantity,
            "itemStyle": {"color": color, "rotate": rotate},
            "label": {"fontSize": 10},
        })

    return (trade_price_records, trade_quantity_records)


def get_daily_trade_marker_from_trades_for_render(trades):
    trade_price_records = []
    trade_quantity_records = []

    for trade in trades:
        symbol = trade.symbol
        orders = trade.orders.all()
        for order in orders:
            filled_date = order.filled_time.date()
            filled_price = order.avg_price
            filled_quantity = order.filled_quantity
            coord = [
                filled_date.strftime("%Y/%m/%d"),
                # use high price avoid block candle
                get_swing_daily_candle_y_by_date_action(
                    symbol, filled_date, order.action),
            ]
            color, sign, rotate, escape = get_label_style_from_action(
                order.action)
            trade_price_records.append({
                "name": "{}{}".format(escape, filled_price),
                "coord": coord,
                "value": filled_price,
                "itemStyle": {"color": color, "rotate": rotate},
                "label": {"fontSize": 10},
            })
            trade_quantity_records.append({
                "name": "{}{}{}".format(escape, sign, filled_quantity),
                "coord": coord,
                "value": filled_quantity,
                "itemStyle": {"color": color, "rotate": rotate},
                "label": {"fontSize": 10},
            })

    return (trade_price_records, trade_quantity_records)
