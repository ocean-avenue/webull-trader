import pandas as pd
from datetime import date, datetime
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from sdk import fmpsdk
from common import utils, config, db
from common.enums import SetupType, TradingHourType
from webull_trader.models import DayTrade, EarningCalendar, HistoricalDayTradePerformance, HistoricalMarketStatistics, \
    HistoricalMinuteBar, StockQuote, SwingHistoricalDailyBar, SwingPosition, SwingTrade, WebullAccountStatistics, \
    WebullNews, TradingLog, ExceptionLog, WebullOrder

# Create your views here.


@login_required
def index(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # account statistics data
    net_account_value = {
        "value": "$0.0",
        "total_pl": "0.0",
        "total_pl_style": "badge-soft-dark",
        "total_pl_rate": "0.0%",
        "total_pl_rate_style": "badge-soft-dark",
    }

    last_acc_stat = WebullAccountStatistics.objects.last()
    if last_acc_stat:
        net_account_value["value"] = "${}".format(
            last_acc_stat.net_liquidation)

        net_account_value["total_pl"] = "{}".format(
            round(last_acc_stat.total_profit_loss, 2))
        if last_acc_stat.total_profit_loss > 0:
            net_account_value["total_pl"] = "+" + net_account_value["total_pl"]
            net_account_value["total_pl_style"] = "badge-soft-success"
        elif last_acc_stat.total_profit_loss < 0:
            net_account_value["total_pl_style"] = "badge-soft-danger"

        net_account_value["total_pl_rate"] = "{}%".format(
            round(last_acc_stat.total_profit_loss_rate * 100, 2))
        if last_acc_stat.total_profit_loss_rate > 0:
            net_account_value["total_pl_rate"] = "+" + \
                net_account_value["total_pl_rate"]
            net_account_value["total_pl_rate_style"] = "badge-soft-success"
        elif last_acc_stat.total_profit_loss_rate < 0:
            net_account_value["total_pl_rate_style"] = "badge-soft-danger"

    today_acc_stat = WebullAccountStatistics.objects.filter(
        date=today).first()
    day_profit_loss = utils.get_net_profit_loss_for_render(today_acc_stat)

    acc_stat_list = WebullAccountStatistics.objects.all()
    # net assets & min usable cash chart
    net_daily_values = []
    net_cash_daily_dates = []
    cash_daily_values = []
    # profit loss chart
    profit_loss_daily_values = []
    profit_loss_daily_dates = []

    for acc_stat in acc_stat_list:
        net_daily_values.append(acc_stat.net_liquidation)
        cash_daily_values.append(acc_stat.min_usable_cash)
        net_cash_daily_dates.append(acc_stat.date.strftime("%Y/%m/%d"))
        profit_loss_daily_values.append(
            utils.get_color_bar_chart_item_for_render(acc_stat.day_profit_loss))
        profit_loss_daily_dates.append(acc_stat.date.strftime("%Y/%m/%d"))

    net_cash = {
        'net_daily_values': net_daily_values,
        'cash_daily_values': cash_daily_values,
        'daily_dates': net_cash_daily_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    profit_loss = {
        'daily_values': profit_loss_daily_values,
        'daily_dates': profit_loss_daily_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    return render(request, 'webull_trader/index.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "net_account_value": net_account_value,
        "day_profit_loss": day_profit_loss,
        "net_cash": net_cash,
        "profit_loss": profit_loss,
    })


@login_required
def logs(request):
    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    trading_logs = []
    trading_log_list = list(TradingLog.objects.order_by('-id')[:100])
    for log in trading_log_list:
        log: TradingLog = log
        days = (date.today() - log.date).days
        text_style = "text-muted"
        if days == 0:
            days_ago = "Today"
            text_style = "text-success"
        elif days == 1:
            days_ago = "Yesterday"
        else:
            days_ago = "{}d ago".format(days)
        trading_hour = "regular"
        if log.trading_hour == TradingHourType.AFTER_MARKET_CLOSE:
            trading_hour = "amc"
        elif log.trading_hour == TradingHourType.BEFORE_MARKET_OPEN:
            trading_hour = "bmo"
        trading_logs.append({
            "date_hour": "{} ({})".format(
                log.date.strftime("%b %d, %Y"),
                TradingHourType.tostr(log.trading_hour)),
            "tag": log.tag,
            "days_ago": days_ago,
            "date_hour_url": "{}/{}".format(log.date.strftime("%Y-%m-%d"), trading_hour),
            "text_style": text_style,
        })
    exception_logs = []
    exception_log_list = list(ExceptionLog.objects.order_by('-id')[:10])
    for log in exception_log_list:
        days = (date.today() - log.created_at.date()).days
        text_style = "text-muted"
        if days == 0:
            days_ago = "Today"
            text_style = "text-danger"
        elif days == 1:
            days_ago = "Yesterday"
        else:
            days_ago = "{}d ago".format(days)
        log_lines = log.log_text.splitlines()
        trace_lines = log.traceback.splitlines()
        exception_logs.append({
            "exception": log.exception,
            "traceback": log.traceback,
            "log_lines": log_lines,
            "trace_lines": trace_lines,
            "date_time": log.created_at.strftime("%b %d, %Y %H:%M"),
            "days_ago": days_ago,
            "text_style": text_style,
        })

    return render(request, 'webull_trader/logs.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "trading_logs": trading_logs,
        "exception_logs": exception_logs,
    })


@login_required
def trading_logs_date_hour(request, date=None, hour=None):
    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    if hour == "regular":
        trading_hour = TradingHourType.REGULAR
    elif hour == "bmo":
        trading_hour = TradingHourType.BEFORE_MARKET_OPEN
    elif hour == "amc":
        trading_hour = TradingHourType.AFTER_MARKET_CLOSE

    log = get_object_or_404(TradingLog, date=date, trading_hour=trading_hour)
    log_lines = log.log_text.splitlines()

    return render(request, 'webull_trader/trading_logs_date_hour.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "log_lines": log_lines,
        "date": log.date.strftime("%Y-%m-%d"),
        "trading_hour": TradingHourType.tostr(log.trading_hour),
    })


@login_required
def day_analytics(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # calendar events
    profit_events = {
        "events": [],
        "color": config.PROFIT_COLOR,
    }

    loss_events = {
        "events": [],
        "color": config.LOSS_COLOR,
    }

    daytrade_perfs = HistoricalDayTradePerformance.objects.all()

    for daytrade_perf in daytrade_perfs:
        # calendar events
        event_date = daytrade_perf.date.strftime("%Y-%m-%d")
        event_url = "/day-analytics/{}".format(event_date)
        target_events = None
        if daytrade_perf.day_profit_loss < 0:
            loss_events['events'].append({
                "title": "-${}".format(abs(daytrade_perf.day_profit_loss)),
                "start": event_date,
                "url": event_url,
            })
            target_events = loss_events
        else:
            profit_events['events'].append({
                "title": "+${}".format(abs(daytrade_perf.day_profit_loss)),
                "start": event_date,
                "url": event_url,
            })
            target_events = profit_events
        target_events['events'].append({
            "title": "{}% win rate".format(daytrade_perf.win_rate),
            "start": event_date,
            "url": event_url,
        })
        target_events['events'].append({
            "title": "{} profit/loss ratio".format(daytrade_perf.profit_loss_ratio),
            "start": event_date,
            "url": event_url,
        })
        target_events['events'].append({
            "title": "{} trades".format(daytrade_perf.trades),
            "start": event_date,
            "url": event_url,
        })

    market_stat_list = HistoricalMarketStatistics.objects.all()
    # top gainer/loser change chart
    top_gainer_daily_values = []
    pre_gainer_daily_values = []
    top_loser_daily_values = []
    pre_loser_daily_values = []
    market_stat_daily_dates = []

    for stat in market_stat_list:
        top_gainer_daily_values.append(round(stat.top_gainer_change * 100, 2))
        pre_gainer_daily_values.append(round(stat.pre_gainer_change * 100, 2))
        top_loser_daily_values.append(round(stat.top_loser_change * 100, 2))
        pre_loser_daily_values.append(round(stat.pre_loser_change * 100, 2))
        market_stat_daily_dates.append(stat.date.strftime("%Y/%m/%d"))

    market_stat = {
        'gainer_daily_values': top_gainer_daily_values,
        'pre_gainer_daily_values': pre_gainer_daily_values,
        'loser_daily_values': top_loser_daily_values,
        'pre_loser_daily_values': pre_loser_daily_values,
        'daily_dates': market_stat_daily_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    plwin_daily_values = []
    perf_stat_dates = []

    daytrade_perfs = HistoricalDayTradePerformance.objects.all()
    for daytrade_perf in daytrade_perfs:
        perf_stat_dates.append(daytrade_perf.date.strftime("%Y/%m/%d"))
        plwin_daily_values.append(
            round(daytrade_perf.profit_loss_ratio * daytrade_perf.win_rate, 2))

    perf_stat = {
        'plwin_daily_values': plwin_daily_values,
        'daily_dates': perf_stat_dates,
        'weekly_values': [],  # TODO
        'weekly_dates': [],  # TODO
        'monthly_values': [],  # TODO
        'monthly_dates': [],  # TODO
    }

    return render(request, 'webull_trader/day_analytics.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "initial_date": today.strftime("%Y-%m-%d"),
        "profit_events": profit_events,
        "loss_events": loss_events,
        "market_stat": market_stat,
        "perf_stat": perf_stat,
    })


@login_required
def day_analytics_date(request, date=None):
    daytrade_perf = get_object_or_404(HistoricalDayTradePerformance, date=date)
    acc_stat = get_object_or_404(WebullAccountStatistics, date=date)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day profit loss
    day_profit_loss = utils.get_day_profit_loss_for_render(daytrade_perf)
    # top gain & loss
    day_top_gain = {
        "value": "+${}".format(daytrade_perf.top_gain_amount),
        "symbol": daytrade_perf.top_gain_symbol
    }
    day_top_loss = {
        "value": "-${}".format(abs(daytrade_perf.top_loss_amount)),
        "symbol": daytrade_perf.top_loss_symbol
    }

    # day trades
    day_trades = DayTrade.objects.filter(
        sell_date=acc_stat.date, require_adjustment=False)
    print(len(day_trades))
    hourly_statistics = utils.get_stats_empty_list(size=32)
    # for hourly P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        hourly_idx = utils.get_market_hourly_interval_index(
            utils.local_datetime(day_trade.buy_time))
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
        hourly_profit_loss.append(utils.get_color_bar_chart_item_for_render(
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

    # for trade records group by symbol
    trades_dist = utils.get_trade_stat_dist_from_day_trades(day_trades)
    # trade records
    trade_records = []
    for symbol, trade_stat in trades_dist.items():
        trade_record_for_render = utils.get_day_trade_stat_record_for_render(
            symbol, trade_stat, acc_stat.date)
        trade_records.append(trade_record_for_render)
    # sort trade records
    trade_records.sort(key=lambda t: t['profit_loss_value'], reverse=True)

    return render(request, 'webull_trader/day_analytics_date.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "date": date,
        "day_profit_loss": day_profit_loss,
        "trades_count": daytrade_perf.trades,
        "day_top_gain": day_top_gain,
        "day_top_loss": day_top_loss,
        "win_rate": "{}%".format(daytrade_perf.win_rate),
        "profit_loss_ratio": daytrade_perf.profit_loss_ratio,
        "hourly_labels": utils.get_market_hourly_interval_labels(),
        "hourly_profit_loss": hourly_profit_loss,
        "hourly_win_rate": hourly_win_rate,
        "hourly_profit_loss_ratio": hourly_profit_loss_ratio,
        "hourly_trades": hourly_trades,
        "trade_records": trade_records,
    })


@login_required
def day_analytics_date_symbol(request, date=None, symbol=None):
    # minute_bars = get_list_or_404(
    #     HistoricalMinuteBar, date=date, symbol=symbol)

    minute_bars = HistoricalMinuteBar.objects.filter(symbol=symbol, date=date)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    timestamps = []
    # for load data frame
    m1_data_for_df = {
        "open": [],
        "high": [],
        "low": [],
        "close": [],
        "volume": [],
        "vwap": [],
    }
    for minute_bar in minute_bars:
        timestamps.append(minute_bar.time)
        m1_data_for_df['open'].append(minute_bar.open)
        m1_data_for_df['high'].append(minute_bar.high)
        m1_data_for_df['low'].append(minute_bar.low)
        m1_data_for_df['close'].append(minute_bar.close)
        m1_data_for_df['volume'].append(minute_bar.volume)
        m1_data_for_df['vwap'].append(minute_bar.vwap)

    m1_bars = pd.DataFrame(m1_data_for_df, index=timestamps)
    # calculate and fill ema 9 data
    m1_bars['ema9'] = m1_bars['close'].ewm(span=9, adjust=False).mean()
    # load 1m data for render
    m1_candle_data = utils.get_minute_candle_data_for_render(m1_bars)
    # calculate 2m bars
    m2_bars = utils.convert_2m_bars(m1_bars)
    # calculate and fill ema 9 data
    if not m2_bars.empty:
        m2_bars['ema9'] = m2_bars['close'].ewm(span=9, adjust=False).mean()
    # load 2m data for render
    m2_candle_data = utils.get_minute_candle_data_for_render(m2_bars)
    # calculate 5m bars
    m5_bars = utils.convert_5m_bars(m1_bars)
    # calculate and fill ema 9 data
    if not m5_bars.empty:
        m5_bars['ema9'] = m5_bars['close'].ewm(span=9, adjust=False).mean()
    # load 5m data for render
    m5_candle_data = utils.get_minute_candle_data_for_render(m5_bars)
    # analytics date
    analytics_date = datetime.strptime(date, '%Y-%m-%d').date()
    # calculate daily candle
    d1_candle_data = utils.get_last_60d_daily_candle_data_for_render(
        symbol, analytics_date)
    # buy/sell orders
    buy_orders, sell_orders = utils.get_day_trade_orders(
        date=analytics_date, symbol=symbol)
    # 1m trade records
    m1_trade_price_buy_records, m1_trade_quantity_buy_records = utils.get_minutes_trade_marker_from_orders_for_render(
        buy_orders, m1_candle_data, 1)
    m1_trade_price_sell_records, m1_trade_quantity_sell_records = utils.get_minutes_trade_marker_from_orders_for_render(
        sell_orders, m1_candle_data, 1)
    m1_trade_price_records = m1_trade_price_buy_records + m1_trade_price_sell_records
    m1_trade_quantity_records = m1_trade_quantity_buy_records + \
        m1_trade_quantity_sell_records
    # 2m trade records
    m2_trade_price_buy_records, m2_trade_quantity_buy_records = utils.get_minutes_trade_marker_from_orders_for_render(
        buy_orders, m2_candle_data, 2)
    m2_trade_price_sell_records, m2_trade_quantity_sell_records = utils.get_minutes_trade_marker_from_orders_for_render(
        sell_orders, m2_candle_data, 2)
    m2_trade_price_records = m2_trade_price_buy_records + m2_trade_price_sell_records
    m2_trade_quantity_records = m2_trade_quantity_buy_records + \
        m2_trade_quantity_sell_records
    # 5m trade records
    m5_trade_price_buy_records, m5_trade_quantity_buy_records = utils.get_minutes_trade_marker_from_orders_for_render(
        buy_orders, m5_candle_data, 5)
    m5_trade_price_sell_records, m5_trade_quantity_sell_records = utils.get_minutes_trade_marker_from_orders_for_render(
        sell_orders, m5_candle_data, 5)
    m5_trade_price_records = m5_trade_price_buy_records + m5_trade_price_sell_records
    m5_trade_quantity_records = m5_trade_quantity_buy_records + \
        m5_trade_quantity_sell_records

    # day trades
    day_trades = DayTrade.objects.filter(
        symbol=symbol, sell_date=analytics_date, require_adjustment=False)
    trade_records = []
    for day_trade in day_trades:
        buy_price = round(day_trade.total_cost / day_trade.quantity, 3)
        sell_price = round(day_trade.total_sold / day_trade.quantity, 3)
        quantity = day_trade.quantity
        units = day_trade.units
        gain = round(day_trade.total_sold - day_trade.total_cost, 3)
        profit_loss, profit_loss_style = utils.get_color_price_style_for_render(
            gain)
        profit_loss_percent = "{}%".format(
            round(gain / day_trade.total_cost * 100, 2))
        if gain >= 0:
            profit_loss_percent = "+{}".format(profit_loss_percent)

        order_ids = day_trade.order_ids.split(",")
        buy_order_id = order_ids[0]
        sell_order_id = order_ids[-1]

        setup = None
        buy_order = WebullOrder.objects.filter(order_id=buy_order_id).first()
        if buy_order:
            setup = SetupType.tostr(buy_order.setup)
        note = None
        sell_order = WebullOrder.objects.filter(order_id=sell_order_id).first()
        if sell_order:
            note = sell_order.note or ""
        trade_records.append({
            "symbol": symbol,
            "quantity": quantity,
            "units": units,
            "total_cost": "${}".format(day_trade.total_cost),
            "buy_price": "${}".format(buy_price),
            "sell_price": "${}".format(sell_price),
            "buy_time": utils.local_time_minute_second(day_trade.buy_time),
            "sell_time": utils.local_time_minute_second(day_trade.sell_time),
            "setup": setup,
            "note": note,
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent,
            "profit_loss_style": profit_loss_style,
        })

    # stats
    trades_dist = utils.get_trade_stat_dist_from_day_trades(day_trades)
    trade_stats = utils.get_day_trade_stat_record_for_render(
        symbol, trades_dist[symbol], date)
    # news
    webull_news = WebullNews.objects.filter(
        symbol=symbol).filter(date=date)
    news = []
    for webull_new in webull_news:
        news.append({
            'title': webull_new.title,
            'source_name': webull_new.source_name,
            'collect_source': webull_new.collect_source,
            'news_time': webull_new.news_time.split('.')[0].replace("T", " "),
            'summary': webull_new.summary,
            'news_url': webull_new.news_url,
        })
    # hourly stats
    hourly_stat = utils.get_hourly_stat_from_trades_for_render(day_trades)

    return render(request, 'webull_trader/day_analytics_date_symbol.html', {
        "date": date,
        "symbol": symbol,
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "m1_candle_data": m1_candle_data,
        "m2_candle_data": m2_candle_data,
        "m5_candle_data": m5_candle_data,
        "m1_trade_price_records": m1_trade_price_records,
        "m1_trade_quantity_records": m1_trade_quantity_records,
        "m2_trade_price_records": m2_trade_price_records,
        "m2_trade_quantity_records": m2_trade_quantity_records,
        "m5_trade_price_records": m5_trade_price_records,
        "m5_trade_quantity_records": m5_trade_quantity_records,
        "d1_candle_data": d1_candle_data,
        "trade_records": trade_records,
        "trade_stats": trade_stats,
        "news": news,
        "hourly_labels": utils.get_market_hourly_interval_labels(),
        "hourly_profit_loss": hourly_stat['profit_loss'],
    })


@login_required
def day_reports_price(request):

    cached_context = cache.get('day_reports_price_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    price_statistics = utils.get_stats_empty_list(size=16)
    # for price range P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        buy_price = (day_trade.total_cost / day_trade.quantity)
        price_idx = utils.get_entry_price_range_index(buy_price)
        gain = day_trade.total_sold - day_trade.total_cost
        if gain > 0:
            price_statistics[price_idx]['win_trades'] += 1
            price_statistics[price_idx]['total_profit'] += gain
        else:
            price_statistics[price_idx]['loss_trades'] += 1
            price_statistics[price_idx]['total_loss'] += gain
        price_statistics[price_idx]['profit_loss'] += gain
        price_statistics[price_idx]['trades'] += 1
    price_profit_loss = []
    price_total_profit = []
    price_total_loss = []
    price_win_rate = []
    price_profit_loss_ratio = []
    price_trades = []
    # calculate win rate and profit/loss ratio
    for price_stat in price_statistics:
        price_trades.append(price_stat['trades'])
        price_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(price_stat['profit_loss'], 2)))
        price_total_profit.append(round(price_stat['total_profit'], 2))
        price_total_loss.append(round(price_stat['total_loss'], 2))
        if price_stat['trades'] > 0:
            price_win_rate.append(
                round(price_stat['win_trades']/price_stat['trades'] * 100, 2))
        else:
            price_win_rate.append(0.0)
        avg_profit = 1.0
        if price_stat['win_trades'] > 0:
            avg_profit = price_stat['total_profit'] / \
                price_stat['win_trades']
        avg_loss = 1.0
        if price_stat['loss_trades'] > 0:
            avg_loss = price_stat['total_loss'] / price_stat['loss_trades']
        profit_loss_ratio = 0.0
        if price_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if price_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        price_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Entry Price",
        "labels": utils.get_entry_price_range_labels(),
        "profit_loss": price_profit_loss,
        "total_profit": price_total_profit,
        "total_loss": price_total_loss,
        "win_rate": price_win_rate,
        "profit_loss_ratio": price_profit_loss_ratio,
        "trades": price_trades,
    }

    cache.set('day_reports_price_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_mktcap(request):

    cached_context = cache.get('day_reports_mktcap_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    stat_render = utils.get_value_stat_from_trades_for_render(
        day_trades,
        "market_value",
        utils.get_market_cap_range_index,
        utils.get_market_cap_range_labels())

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Market Cap",
        "labels": utils.get_market_cap_range_labels(),
        "profit_loss": stat_render['profit_loss'],
        "total_profit": stat_render['total_profit'],
        "total_loss": stat_render['total_loss'],
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_mktcap_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_float(request):

    cached_context = cache.get('day_reports_float_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    stat_render = utils.get_value_stat_from_trades_for_render(
        day_trades,
        "outstanding_shares",
        utils.get_free_float_range_index,
        utils.get_free_float_range_labels())

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Free Float",
        "labels": utils.get_free_float_range_labels(),
        "profit_loss": stat_render['profit_loss'],
        "total_profit": stat_render['total_profit'],
        "total_loss": stat_render['total_loss'],
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_float_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_turnover(request):

    cached_context = cache.get('day_reports_turnover_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    stat_render = utils.get_value_stat_from_trades_for_render(
        day_trades,
        "turnover_rate",
        utils.get_turnover_ratio_range_index,
        utils.get_turnover_ratio_range_labels())

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Turnover %",
        "labels": utils.get_turnover_ratio_range_labels(),
        "profit_loss": stat_render['profit_loss'],
        "total_profit": stat_render['total_profit'],
        "total_loss": stat_render['total_loss'],
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_turnover_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_short(request):

    cached_context = cache.get('day_reports_short_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    stat_render = utils.get_value_stat_from_trades_for_render(
        day_trades,
        "short_float",
        utils.get_short_float_range_index,
        utils.get_short_float_range_labels())

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Short Ratio",
        "labels": utils.get_short_float_range_labels(),
        "profit_loss": stat_render['profit_loss'],
        "total_profit": stat_render['total_profit'],
        "total_loss": stat_render['total_loss'],
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_short_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_gap(request):

    cached_context = cache.get('day_reports_gap_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    gap_statistics = utils.get_stats_empty_list(
        size=len(utils.get_gap_range_labels()))
    # for P&L, win rate and profit/loss ratio, trades by gap
    for day_trade in day_trades:
        gap = utils.get_gap_by_symbol_date(
            day_trade.symbol, day_trade.buy_date)
        gap_idx = utils.get_gap_range_index(gap)
        gain = day_trade.total_sold - day_trade.total_cost
        if gain > 0:
            gap_statistics[gap_idx]['win_trades'] += 1
            gap_statistics[gap_idx]['total_profit'] += gain
        else:
            gap_statistics[gap_idx]['loss_trades'] += 1
            gap_statistics[gap_idx]['total_loss'] += gain
        gap_statistics[gap_idx]['profit_loss'] += gain
        gap_statistics[gap_idx]['trades'] += 1
    gap_profit_loss = []
    gap_total_profit = []
    gap_total_loss = []
    gap_win_rate = []
    gap_profit_loss_ratio = []
    gap_trades = []
    # calculate win rate and profit/loss ratio
    for gap_stat in gap_statistics:
        gap_trades.append(gap_stat['trades'])
        gap_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(gap_stat['profit_loss'], 2)))
        gap_total_profit.append(round(gap_stat['total_profit'], 2))
        gap_total_loss.append(round(gap_stat['total_loss'], 2))
        if gap_stat['trades'] > 0:
            gap_win_rate.append(
                round(gap_stat['win_trades']/gap_stat['trades'] * 100, 2))
        else:
            gap_win_rate.append(0.0)
        avg_profit = 1.0
        if gap_stat['win_trades'] > 0:
            avg_profit = gap_stat['total_profit'] / \
                gap_stat['win_trades']
        avg_loss = 1.0
        if gap_stat['loss_trades'] > 0:
            avg_loss = gap_stat['total_loss'] / gap_stat['loss_trades']
        profit_loss_ratio = 0.0
        if gap_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if gap_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        gap_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Gap %",
        "labels": utils.get_gap_range_labels(),
        "profit_loss": gap_profit_loss,
        "total_profit": gap_total_profit,
        "total_loss": gap_total_loss,
        "win_rate": gap_win_rate,
        "profit_loss_ratio": gap_profit_loss_ratio,
        "trades": gap_trades,
    }

    cache.set('day_reports_gap_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_relvol(request):

    cached_context = cache.get('day_reports_relvol_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    relvol_statistics = utils.get_stats_empty_list(
        size=len(utils.get_relative_volume_labels()))
    # for P&L, win rate and profit/loss ratio, trades by relative volume
    for day_trade in day_trades:
        symbol = day_trade.symbol
        buy_date = day_trade.buy_date
        key_statistics = db.get_hist_key_stat(symbol, buy_date)
        if key_statistics:
            relative_volume = round(
                key_statistics.volume / key_statistics.avg_vol_3m, 2)
            relvol_idx = utils.get_relative_volume_index(relative_volume)
            gain = day_trade.total_sold - day_trade.total_cost
            if gain > 0:
                relvol_statistics[relvol_idx]['win_trades'] += 1
                relvol_statistics[relvol_idx]['total_profit'] += gain
            else:
                relvol_statistics[relvol_idx]['loss_trades'] += 1
                relvol_statistics[relvol_idx]['total_loss'] += gain
            relvol_statistics[relvol_idx]['profit_loss'] += gain
            relvol_statistics[relvol_idx]['trades'] += 1
    relvol_profit_loss = []
    relvol_total_profit = []
    relvol_total_loss = []
    relvol_win_rate = []
    relvol_profit_loss_ratio = []
    relvol_trades = []
    # calculate win rate and profit/loss ratio
    for relvol_stat in relvol_statistics:
        relvol_trades.append(relvol_stat['trades'])
        relvol_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(relvol_stat['profit_loss'], 2)))
        relvol_total_profit.append(round(relvol_stat['total_profit'], 2))
        relvol_total_loss.append(round(relvol_stat['total_loss'], 2))
        if relvol_stat['trades'] > 0:
            relvol_win_rate.append(
                round(relvol_stat['win_trades']/relvol_stat['trades'] * 100, 2))
        else:
            relvol_win_rate.append(0.0)
        avg_profit = 1.0
        if relvol_stat['win_trades'] > 0:
            avg_profit = relvol_stat['total_profit'] / \
                relvol_stat['win_trades']
        avg_loss = 1.0
        if relvol_stat['loss_trades'] > 0:
            avg_loss = relvol_stat['total_loss'] / relvol_stat['loss_trades']
        profit_loss_ratio = 0.0
        if relvol_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if relvol_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        relvol_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Relative Volume",
        "labels": utils.get_relative_volume_labels(),
        "profit_loss": relvol_profit_loss,
        "total_profit": relvol_total_profit,
        "total_loss": relvol_total_loss,
        "win_rate": relvol_win_rate,
        "profit_loss_ratio": relvol_profit_loss_ratio,
        "trades": relvol_trades,
    }

    cache.set('day_reports_relvol_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_sector(request):

    cached_context = cache.get('day_reports_sector_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    sector_statistics = utils.get_stats_empty_list(
        size=len(utils.get_sector_labels()))
    # for P&L, win rate and profit/loss ratio, trades by sector
    for day_trade in day_trades:
        sector = None
        quote = StockQuote.objects.filter(symbol=day_trade.symbol).first()
        if quote:
            sector = quote.sector
        sector_idx = utils.get_sector_index(sector)
        gain = day_trade.total_sold - day_trade.total_cost
        if gain > 0:
            sector_statistics[sector_idx]['win_trades'] += 1
            sector_statistics[sector_idx]['total_profit'] += gain
        else:
            sector_statistics[sector_idx]['loss_trades'] += 1
            sector_statistics[sector_idx]['total_loss'] += gain
        sector_statistics[sector_idx]['profit_loss'] += gain
        sector_statistics[sector_idx]['trades'] += 1
    sector_profit_loss = []
    sector_total_profit = []
    sector_total_loss = []
    sector_win_rate = []
    sector_profit_loss_ratio = []
    sector_trades = []
    # calculate win rate and profit/loss ratio
    for sector_stat in sector_statistics:
        sector_trades.append(sector_stat['trades'])
        sector_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(sector_stat['profit_loss'], 2)))
        sector_total_profit.append(round(sector_stat['total_profit'], 2))
        sector_total_loss.append(round(sector_stat['total_loss'], 2))
        if sector_stat['trades'] > 0:
            sector_win_rate.append(
                round(sector_stat['win_trades']/sector_stat['trades'] * 100, 2))
        else:
            sector_win_rate.append(0.0)
        avg_profit = 1.0
        if sector_stat['win_trades'] > 0:
            avg_profit = sector_stat['total_profit'] / \
                sector_stat['win_trades']
        avg_loss = 1.0
        if sector_stat['loss_trades'] > 0:
            avg_loss = sector_stat['total_loss'] / sector_stat['loss_trades']
        profit_loss_ratio = 0.0
        if sector_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if sector_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        sector_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Sector",
        "labels": utils.get_sector_labels(),
        "profit_loss": sector_profit_loss,
        "total_profit": sector_total_profit,
        "total_loss": sector_total_loss,
        "win_rate": sector_win_rate,
        "profit_loss_ratio": sector_profit_loss_ratio,
        "trades": sector_trades,
    }

    cache.set('day_reports_sector_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_holding(request):

    cached_context = cache.get('day_reports_holding_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    holding_statistics = utils.get_stats_empty_list(
        size=len(utils.get_holding_time_labels()))
    # for P&L, win rate and profit/loss ratio, trades by holding time
    for day_trade in day_trades:
        holding_sec = (day_trade.sell_time - day_trade.buy_time).seconds
        holding_idx = utils.get_holding_time_index(holding_sec)
        gain = day_trade.total_sold - day_trade.total_cost
        if gain > 0:
            holding_statistics[holding_idx]['win_trades'] += 1
            holding_statistics[holding_idx]['total_profit'] += gain
        else:
            holding_statistics[holding_idx]['loss_trades'] += 1
            holding_statistics[holding_idx]['total_loss'] += gain
        holding_statistics[holding_idx]['profit_loss'] += gain
        holding_statistics[holding_idx]['trades'] += 1
    holding_profit_loss = []
    holding_total_profit = []
    holding_total_loss = []
    holding_win_rate = []
    holding_profit_loss_ratio = []
    holding_trades = []
    # calculate win rate and profit/loss ratio
    for holding_stat in holding_statistics:
        holding_trades.append(holding_stat['trades'])
        holding_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(holding_stat['profit_loss'], 2)))
        holding_total_profit.append(round(holding_stat['total_profit'], 2))
        holding_total_loss.append(round(holding_stat['total_loss'], 2))
        if holding_stat['trades'] > 0:
            holding_win_rate.append(
                round(holding_stat['win_trades']/holding_stat['trades'] * 100, 2))
        else:
            holding_win_rate.append(0.0)
        avg_profit = 1.0
        if holding_stat['win_trades'] > 0:
            avg_profit = holding_stat['total_profit'] / \
                holding_stat['win_trades']
        avg_loss = 1.0
        if holding_stat['loss_trades'] > 0:
            avg_loss = holding_stat['total_loss'] / holding_stat['loss_trades']
        profit_loss_ratio = 0.0
        if holding_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if holding_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        holding_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Holding Time",
        "labels": utils.get_holding_time_labels(),
        "profit_loss": holding_profit_loss,
        "total_profit": holding_total_profit,
        "total_loss": holding_total_loss,
        "win_rate": holding_win_rate,
        "profit_loss_ratio": holding_profit_loss_ratio,
        "trades": holding_trades,
    }

    cache.set('day_reports_holding_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_plpct(request):

    cached_context = cache.get('day_reports_plpct_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_field.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    plpct_statistics = utils.get_stats_empty_list(
        size=len(utils.get_plpct_range_labels()))
    # for P&L, win rate and profit/loss ratio, trades by P/L percentage
    for day_trade in day_trades:
        percentage = round(
            (day_trade.total_sold - day_trade.total_cost) / day_trade.total_cost * 100, 2)
        percentage_idx = utils.get_plpct_range_index(percentage)
        gain = day_trade.total_sold - day_trade.total_cost
        if gain > 0:
            plpct_statistics[percentage_idx]['win_trades'] += 1
            plpct_statistics[percentage_idx]['total_profit'] += gain
        else:
            plpct_statistics[percentage_idx]['loss_trades'] += 1
            plpct_statistics[percentage_idx]['total_loss'] += gain
        plpct_statistics[percentage_idx]['profit_loss'] += gain
        plpct_statistics[percentage_idx]['trades'] += 1
    plpct_profit_loss = []
    plpct_total_profit = []
    plpct_total_loss = []
    plpct_win_rate = []
    plpct_profit_loss_ratio = []
    plpct_trades = []
    # calculate win rate and profit/loss ratio
    for holding_stat in plpct_statistics:
        plpct_trades.append(holding_stat['trades'])
        plpct_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(holding_stat['profit_loss'], 2)))
        plpct_total_profit.append(round(holding_stat['total_profit'], 2))
        plpct_total_loss.append(round(holding_stat['total_loss'], 2))
        if holding_stat['trades'] > 0:
            plpct_win_rate.append(
                round(holding_stat['win_trades']/holding_stat['trades'] * 100, 2))
        else:
            plpct_win_rate.append(0.0)
        avg_profit = 1.0
        if holding_stat['win_trades'] > 0:
            avg_profit = holding_stat['total_profit'] / \
                holding_stat['win_trades']
        avg_loss = 1.0
        if holding_stat['loss_trades'] > 0:
            avg_loss = holding_stat['total_loss'] / holding_stat['loss_trades']
        profit_loss_ratio = 0.0
        if holding_stat['trades'] > 0:
            profit_loss_ratio = 1.0
        if holding_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        plpct_profit_loss_ratio.append(profit_loss_ratio)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "P/L %",
        "labels": utils.get_plpct_range_labels(),
        "profit_loss": plpct_profit_loss,
        "total_profit": plpct_total_profit,
        "total_loss": plpct_total_loss,
        "win_rate": plpct_win_rate,
        "profit_loss_ratio": plpct_profit_loss_ratio,
        "trades": plpct_trades,
    }

    cache.set('day_reports_plpct_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_field.html', context)


@login_required
def day_reports_hourly(request):

    cached_context = cache.get('day_reports_hourly_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_hourly.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # day trades
    day_trades = DayTrade.objects.filter(require_adjustment=False)
    hourly_stat = utils.get_hourly_stat_from_trades_for_render(day_trades)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Hourly",
        "hourly_labels": utils.get_market_hourly_interval_labels(),
        "hourly_profit_loss": hourly_stat['profit_loss'],
        "hourly_win_rate": hourly_stat['win_rate'],
        "hourly_profit_loss_ratio": hourly_stat['profit_loss_ratio'],
        "hourly_trades": hourly_stat['trades'],
    }

    cache.set('day_reports_hourly_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_hourly.html', context)


@login_required
def day_reports_daily(request):

    cached_context = cache.get('day_reports_daily_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_daily.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    daily_labels = []
    daily_profit_loss = []
    daily_win_rate = []
    daily_profit_loss_ratio = []
    daily_trades = []
    daytrade_perfs = HistoricalDayTradePerformance.objects.all()
    for daytrade_perf in daytrade_perfs:
        daily_labels.append(daytrade_perf.date.strftime("%Y/%m/%d"))
        daily_profit_loss.append(
            utils.get_color_bar_chart_item_for_render(daytrade_perf.day_profit_loss))
        daily_win_rate.append(daytrade_perf.win_rate)
        daily_profit_loss_ratio.append(daytrade_perf.profit_loss_ratio)
        daily_trades.append(daytrade_perf.trades)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Daily",
        "daily_labels": daily_labels,
        "daily_profit_loss": daily_profit_loss,
        "daily_win_rate": daily_win_rate,
        "daily_profit_loss_ratio": daily_profit_loss_ratio,
        "daily_trades": daily_trades,
    }

    cache.set('day_reports_daily_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_daily.html', context)


@login_required
def day_reports_weekly(request):

    cached_context = cache.get('day_reports_weekly_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_weekly.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    weekly_labels = []
    weekly_profit_loss = []
    weekly_win_rate = []
    weekly_profit_loss_ratio = []
    weekly_trades = []
    daytrade_perfs = HistoricalDayTradePerformance.objects.all()

    last_week_no = -1
    last_week_count = 0
    if daytrade_perfs.first():
        last_week_no = daytrade_perfs.first().date.isocalendar()[1]
    last_week_profit_loss = 0.0
    last_week_win_rate = 0.0
    last_week_profit_loss_ratio = 0.0
    last_week_trades = 0

    for daytrade_perf in daytrade_perfs:
        week_no = daytrade_perf.date.isocalendar()[1]
        if week_no != last_week_no:
            # attach last week data
            weekly_labels.append("Week {}".format(last_week_no))
            weekly_profit_loss.append(
                utils.get_color_bar_chart_item_for_render(round(last_week_profit_loss, 2)))
            weekly_win_rate.append(
                round(last_week_win_rate / last_week_count, 2))
            weekly_profit_loss_ratio.append(
                round(last_week_profit_loss_ratio / last_week_count, 2))
            weekly_trades.append(last_week_trades)
            # reset current week data
            last_week_no = week_no
            last_week_count = 1
            last_week_profit_loss = daytrade_perf.day_profit_loss
            last_week_win_rate = daytrade_perf.win_rate
            last_week_profit_loss_ratio = daytrade_perf.profit_loss_ratio
            last_week_trades = daytrade_perf.trades
        else:
            # accumulate current week data
            last_week_count += 1
            last_week_profit_loss += daytrade_perf.day_profit_loss
            last_week_win_rate += daytrade_perf.win_rate
            last_week_profit_loss_ratio += daytrade_perf.profit_loss_ratio
            last_week_trades += daytrade_perf.trades
    # attach remaining week data
    if last_week_count > 0:
        weekly_labels.append("Week {}".format(last_week_no))
        weekly_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(last_week_profit_loss, 2)))
        weekly_win_rate.append(
            round(last_week_win_rate / last_week_count, 2))
        weekly_profit_loss_ratio.append(
            round(last_week_profit_loss_ratio / last_week_count, 2))
        weekly_trades.append(last_week_trades)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Weekly",
        "weekly_labels": weekly_labels,
        "weekly_profit_loss": weekly_profit_loss,
        "weekly_win_rate": weekly_win_rate,
        "weekly_profit_loss_ratio": weekly_profit_loss_ratio,
        "weekly_trades": weekly_trades,
    }

    cache.set('day_reports_weekly_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_weekly.html', context)


@login_required
def day_reports_monthly(request):

    cached_context = cache.get('day_reports_monthly_cache')
    if cached_context:
        return render(request, 'webull_trader/day_reports_monthly.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    monthly_labels = []
    monthly_profit_loss = []
    monthly_win_rate = []
    monthly_profit_loss_ratio = []
    monthly_trades = []
    daytrade_perfs = HistoricalDayTradePerformance.objects.all()

    last_month_no = "0000/00"
    last_month_count = 0
    if daytrade_perfs.first():
        last_month_no = daytrade_perfs.first().date.strftime("%Y/%m")
    last_month_profit_loss = 0.0
    last_month_win_rate = 0.0
    last_month_profit_loss_ratio = 0.0
    last_month_trades = 0

    for daytrade_perf in daytrade_perfs:
        month_no = daytrade_perf.date.strftime("%Y/%m")
        if month_no != last_month_no:
            # attach last month data
            monthly_labels.append(last_month_no)
            monthly_profit_loss.append(
                utils.get_color_bar_chart_item_for_render(round(last_month_profit_loss, 2)))
            monthly_win_rate.append(
                round(last_month_win_rate / last_month_count, 2))
            monthly_profit_loss_ratio.append(
                round(last_month_profit_loss_ratio / last_month_count, 2))
            monthly_trades.append(last_month_trades)
            # reset current month data
            last_month_no = month_no
            last_month_count = 1
            last_month_profit_loss = daytrade_perf.day_profit_loss
            last_month_win_rate = daytrade_perf.win_rate
            last_month_profit_loss_ratio = daytrade_perf.profit_loss_ratio
            last_month_trades = daytrade_perf.trades
        else:
            # accumulate current month data
            last_month_count += 1
            last_month_profit_loss += daytrade_perf.day_profit_loss
            last_month_win_rate += daytrade_perf.win_rate
            last_month_profit_loss_ratio += daytrade_perf.profit_loss_ratio
            last_month_trades += daytrade_perf.trades
    # attach remaining month data
    if last_month_count > 0:
        monthly_labels.append(last_month_no)
        monthly_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(last_month_profit_loss, 2)))
        monthly_win_rate.append(
            round(last_month_win_rate / last_month_count, 2))
        monthly_profit_loss_ratio.append(
            round(last_month_profit_loss_ratio / last_month_count, 2))
        monthly_trades.append(last_month_trades)

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "title": "Monthly",
        "monthly_labels": monthly_labels,
        "monthly_profit_loss": monthly_profit_loss,
        "monthly_win_rate": monthly_win_rate,
        "monthly_profit_loss_ratio": monthly_profit_loss_ratio,
        "monthly_trades": monthly_trades,
    }

    cache.set('day_reports_monthly_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_monthly.html', context)


@login_required
def swing_positions(request):

    cached_context = cache.get('swing_positions_cache')
    if cached_context:
        return render(request, 'webull_trader/swing_positions.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    positions = SwingPosition.objects.all()
    last_acc_stat = WebullAccountStatistics.objects.last()
    net_liquidation = 0.0
    if last_acc_stat:
        net_liquidation = last_acc_stat.net_liquidation

    swing_positions = []
    for position in positions:
        symbol = position.symbol
        setup = SetupType.tostr(position.setup)
        buy_date = position.buy_date
        holding_days = (date.today() - buy_date).days
        unit_cost = round(position.total_cost / position.quantity, 2)
        quantity = position.quantity
        total_cost = unit_cost * quantity

        last_price = 0.0
        quote = StockQuote.objects.filter(symbol=symbol).first()
        if quote:
            last_price = quote.price

        total_value = last_price * quantity

        portfolio_percent = 0.0
        if net_liquidation > 0:
            portfolio_percent = total_value / net_liquidation

        # position unrealized P&L
        profit_loss, profit_loss_percent, profit_loss_style = utils.get_color_profit_loss_style_for_render(
            total_cost, total_value)

        # position day's P&L
        last_bar = SwingHistoricalDailyBar.objects.filter(symbol=symbol).last()
        day_profit_loss, day_profit_loss_percent, day_profit_loss_style = utils.get_color_profit_loss_style_for_render(
            last_bar.close * quantity, last_price * quantity)

        swing_positions.append({
            "symbol": symbol,
            "unit_cost": "${}".format(unit_cost),
            "total_cost": "${}".format(round(total_cost, 2)),
            "total_value": "${}".format(round(total_value, 2)),
            "quantity": quantity,
            "buy_date": buy_date,
            "holding_days": "{} days".format(holding_days),
            "setup": setup,
            "price": "${}".format(last_price),
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent,
            "profit_loss_style": profit_loss_style,
            "day_profit_loss": day_profit_loss,
            "day_profit_loss_percent": day_profit_loss_percent,
            "day_profit_loss_style": day_profit_loss_style,
            "portfolio_percent": "{}%".format(round(portfolio_percent * 100, 2)),
            "units": position.units,
            "add_unit_price": "${}".format(position.add_unit_price),
            "stop_loss_price": "${}".format(position.stop_loss_price),
        })

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "swing_positions": swing_positions,
    }

    cache.set('swing_positions_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/swing_positions.html', context)


@login_required
def swing_positions_symbol(request, symbol=None):

    cached_context = cache.get(
        'swing_positions_symbol_{}_cache'.format(symbol))
    if cached_context:
        return render(request, 'webull_trader/swing_positions_symbol.html', cached_context)

    position = get_object_or_404(SwingPosition, symbol=symbol)
    quote = get_object_or_404(StockQuote, symbol=symbol)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # fill quote data
    market_value = None
    if quote.market_value:
        market_value = utils.millify(quote.market_value)
    outstanding_shares = None
    if quote.outstanding_shares:
        outstanding_shares = utils.millify(quote.outstanding_shares)
    beta = None
    if quote.beta:
        beta = round(quote.beta, 2)
    pe = None
    if quote.pe:
        pe = round(quote.pe, 2)
    eps = None
    if quote.eps:
        eps = round(quote.eps, 2)
    next_earning = None
    # search next earning
    earnings = EarningCalendar.objects.filter(symbol=symbol)
    for earning in earnings:
        if earning.earning_date >= date.today():
            next_earning = "{} ({})".format(
                earning.earning_date, earning.earning_time)
    change_percent, change_percent_style = utils.get_color_percentage_style_for_render(
        round(quote.change_percentage, 2))
    quote_data = {
        "market_value": market_value,
        "free_float": outstanding_shares,
        "beta": beta,
        "pe": pe,
        "eps": eps,
        "sector": utils.get_quote_sector(quote),
        "next_earning": next_earning,
        "change_percent": change_percent,
        "change_percent_style": change_percent_style,
    }

    # swing position
    unit_cost = round(position.total_cost / position.quantity, 2)
    quantity = position.quantity
    total_cost = unit_cost * quantity
    last_price = quote.price
    total_value = last_price * quantity
    last_acc_stat = WebullAccountStatistics.objects.last()
    net_liquidation = last_acc_stat.net_liquidation
    portfolio_percent = total_value / net_liquidation
    unrealized_pl = total_value - total_cost
    unrealized_pl_percent = (total_value - total_cost) / total_cost

    profit_loss, profit_loss_style = utils.get_color_price_style_for_render(
        round(unrealized_pl, 2))
    swing_position = {
        "unit_cost": "${}".format(unit_cost),
        "total_cost": "${}".format(round(total_cost, 2)),
        "total_value": "${}".format(round(total_value, 2)),
        "quantity": quantity,
        "price": "${}".format(last_price),
        "profit_loss": profit_loss,
        "profit_loss_percent": "{}%".format(round(unrealized_pl_percent * 100, 2)),
        "profit_loss_style": profit_loss_style,
        "portfolio_percent": "{}%".format(round(portfolio_percent * 100, 2)),
        "units": position.units,
        "add_unit_price": "${}".format(position.add_unit_price),
        "stop_loss_price": "${}".format(position.stop_loss_price),
    }

    # calculate daily candle
    d1_candle_data = utils.get_swing_daily_candle_data_for_render(symbol)

    # 1d trade records
    _, d1_trade_quantity_records = utils.get_daily_trade_marker_from_position_for_render(
        position)

    # fmp news
    news = fmpsdk.get_news(symbol, count=16)

    context = {
        "symbol": symbol,
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "quote": quote_data,
        "position": swing_position,
        "d1_candle_data": d1_candle_data,
        "d1_trade_quantity_records": d1_trade_quantity_records,
        "news": news,
    }

    cache.set('swing_positions_symbol_{}_cache'.format(
        symbol), context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/swing_positions_symbol.html', context)


@login_required
def swing_analytics(request):

    cached_context = cache.get('swing_analytics_cache')
    if cached_context:
        return render(request, 'webull_trader/swing_analytics.html', cached_context)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    trades = SwingTrade.objects.all()

    # for trade records group by symbol
    trades_dist = utils.get_trade_stat_dist_from_swing_trades(trades)
    # trade records
    trade_records = []
    # top gain/loss
    top_gain_symbol = ""
    top_gain_value = 0.0
    top_loss_symbol = ""
    top_loss_value = 0.0
    for symbol, trade_stat in trades_dist.items():
        trade_record_for_render = utils.get_swing_trade_stat_record_for_render(
            symbol, trade_stat)
        trade_records.append(trade_record_for_render)
        # calculate top gain/loss
        if trade_stat["top_gain"] > top_gain_value:
            top_gain_symbol = symbol
            top_gain_value = round(trade_stat["top_gain"], 2)
        if trade_stat["top_loss"] < top_loss_value:
            top_loss_symbol = symbol
            top_loss_value = round(trade_stat["top_loss"], 2)

    # sort trade records
    trade_records.sort(key=lambda t: t['profit_loss_value'], reverse=True)

    swing_profit_loss = utils.get_swing_profit_loss_for_render(trades)

    swing_top_gain = {
        "value": "+${}".format(top_gain_value),
        "symbol": top_gain_symbol,
    }
    swing_top_loss = {
        "value": "-${}".format(abs(top_loss_value)),
        "symbol": top_loss_symbol,
    }

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "swing_profit_loss": swing_profit_loss,
        "trade_records": trade_records,
        "trades_count": len(trades),
        "swing_top_gain": swing_top_gain,
        "swing_top_loss": swing_top_loss,
    }

    cache.set('swing_analytics_cache', context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/swing_analytics.html', context)


@login_required
def swing_analytics_symbol(request, symbol=None):

    cached_context = cache.get(
        'swing_analytics_{}_cache'.format(symbol))
    if cached_context:
        return render(request, 'webull_trader/swing_analytics_symbol.html', cached_context)

    trades = get_list_or_404(SwingTrade, symbol=symbol)
    quote = get_object_or_404(StockQuote, symbol=symbol)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # stats
    trades_dist = utils.get_trade_stat_dist_from_swing_trades(trades)
    trade_stats = utils.get_swing_trade_stat_record_for_render(
        symbol, trades_dist[symbol])

    # swing trade records
    trade_records = []
    for trade in trades:
        buy_price = round(trade.total_cost / trade.quantity, 2)
        sell_price = round(trade.total_sold / trade.quantity, 2)
        buy_date = trade.buy_date
        sell_date = trade.sell_date
        quantity = trade.quantity
        units = trade.units
        total_cost = trade.total_cost
        total_sold = trade.total_sold
        realized_pl = total_sold - total_cost
        realized_pl_percent = (total_sold - total_cost) / total_cost
        setup = SetupType.tostr(trade.setup)
        profit_loss, profit_loss_style = utils.get_color_price_style_for_render(
            round(realized_pl, 2))
        profit_loss_percent, profit_loss_percent_style = utils.get_color_percentage_badge_style_for_render(
            round(realized_pl_percent * 100, 2))
        holding_days = (sell_date - buy_date).days
        trade_records.append({
            "buy_price": "${}".format(buy_price),
            "sell_price": "${}".format(sell_price),
            "total_cost": "${}".format(round(total_cost, 2)),
            "total_sold": "${}".format(round(total_sold, 2)),
            "quantity": quantity,
            "units": units,
            "buy_date": buy_date,
            "sell_date": sell_date,
            "holding_days": holding_days,
            "profit_loss": profit_loss,
            "profit_loss_percent": profit_loss_percent,
            "profit_loss_style": profit_loss_style,
            "profit_loss_percent_style": profit_loss_percent_style,
            "setup": setup,
        })

    # calculate daily candle
    d1_candle_data = utils.get_swing_daily_candle_data_for_render(symbol)

    # 1d trade records, only use quantity records for now
    _, d1_trade_quantity_records = utils.get_daily_trade_marker_from_trades_for_render(
        trades)

    context = {
        "symbol": symbol,
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "sector": utils.get_quote_sector(quote),
        "trade_records": trade_records,
        "trade_stats": trade_stats,
        "d1_candle_data": d1_candle_data,
        "d1_trade_quantity_records": d1_trade_quantity_records,
    }

    cache.set('swing_analytics_{}_cache'.format(
        symbol), context, config.CACHE_TIMEOUT)

    return render(request, 'webull_trader/swing_analytics_symbol.html', context)
