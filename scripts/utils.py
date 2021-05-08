import pandas as pd
import numpy as np
import pytz
from django.conf import settings
from datetime import datetime, date
from old_ross import enums
from old_ross.models import HistoricalKeyStatistics, TradingSettings, WebullAccountStatistics, WebullCredentials, WebullNews, WebullOrder, WebullOrderNote, HistoricalMinuteBar, HistoricalDailyBar


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
    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print(
            "[{}] Cannot find trading settings, default paper trading!".format(get_now()))
        return False
    return trading_settings.paper


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


def save_webull_account(acc_data):
    today = date.today()
    print("[{}] Importing daily account status ({})...".format(
        get_now(), today.strftime("%Y-%m-%d")))
    account_members = acc_data['accountMembers']
    day_profit_loss = 0
    for account_member in account_members:
        if account_member['key'] == 'dayProfitLoss':
            day_profit_loss = float(account_member['value'])
    acc_status = WebullAccountStatistics.objects.filter(date=today).first()
    if not acc_status:
        acc_status = WebullAccountStatistics(date=today)
    acc_status.net_liquidation = acc_data['netLiquidation']
    acc_status.total_profit_loss = acc_data['totalProfitLoss']
    acc_status.total_profit_loss_rate = acc_data['totalProfitLossRate']
    acc_status.day_profit_loss = day_profit_loss
    acc_status.save()


def save_webull_order(order_data, paper=True):
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
            status = get_order_status_enum(order_data['statusStr'])
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
                order_type=order_type,
                filled_time=filled_time,
                placed_time=placed_time,
                time_in_force=time_in_force,
                paper=paper,
            )
            order.save()
    else:
        # TODO, support live trade orders
        pass


def save_webull_order_note(order_id, note):
    # TODO, support other setup
    order_note = WebullOrderNote(
        order_id=str(order_id),
        setup=enums.SetupType.DAY_FIRST_CANDLE_NEW_HIGH,
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
            title=news_data['title'],
            source_name=news_data['sourceName'],
            collect_source=news_data['collectSource'],
            news_time=news_data['newsTime'],
            summary=news_data['summary'],
            news_url=news_data['newsUrl'],
            date=date,
        )
        news.save()


def save_hist_key_statistics(quote_data, date):
    symbol = quote_data['symbol']
    print("[{}] Importing key statistics for {}...".format(
        get_now(), symbol))
    key_statistics = HistoricalKeyStatistics.objects.filter(
        symbol=symbol, date=date)
    if not key_statistics:
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
        latest_earnings_date = ''
        if 'latestEarningsDate' in quote_data:
            latest_earnings_date = quote_data['latestEarningsDate']
        estimate_earnings_date = ''
        if 'estimateEarningsDate' in quote_data:
            estimate_earnings_date = quote_data['estimateEarningsDate']
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
            market_value=float(quote_data['marketValue']),
            volume=float(quote_data['volume']),
            turnover_rate=float(quote_data['turnoverRate']),
            vibrate_ratio=float(quote_data['vibrateRatio']),
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
            total_shares=float(quote_data['totalShares']),
            outstanding_shares=float(quote_data['outstandingShares']),
            fifty_two_wk_high=float(quote_data['fiftyTwoWkHigh']),
            fifty_two_wk_low=float(quote_data['fiftyTwoWkLow']),
            latest_earnings_date=latest_earnings_date,
            estimate_earnings_date=estimate_earnings_date,
            date=date,
        )
        key_statistics.save()


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
