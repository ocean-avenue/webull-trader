import pandas as pd
from datetime import date
from django.shortcuts import get_list_or_404, get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from sdk import fmpsdk
from scripts import utils, config
from webull_trader.enums import SetupType
from webull_trader.config import CACHE_TIMEOUT
from webull_trader.models import EarningCalendar, HistoricalDayTradePerformance, HistoricalMinuteBar, SwingHistoricalDailyBar, SwingPosition, SwingWatchlist, WebullAccountStatistics, WebullNews, WebullOrderNote

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
            last_acc_stat.total_profit_loss)
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
    day_profit_loss = utils.get_day_profit_loss_for_render(today_acc_stat)

    acc_stat_list = WebullAccountStatistics.objects.all()
    # net assets chart
    net_assets_daily_values = []
    net_assets_daily_dates = []
    # profit loss chart
    profit_loss_daily_values = []
    profit_loss_daily_dates = []

    for acc_stat in acc_stat_list:
        net_assets_daily_values.append(acc_stat.net_liquidation)
        net_assets_daily_dates.append(acc_stat.date.strftime("%Y/%m/%d"))
        profit_loss_daily_values.append(
            utils.get_color_bar_chart_item_for_render(acc_stat.day_profit_loss))
        profit_loss_daily_dates.append(acc_stat.date.strftime("%Y/%m/%d"))

    net_assets = {
        'daily_values': net_assets_daily_values,
        'daily_dates': net_assets_daily_dates,
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
        "net_assets": net_assets,
        "profit_loss": profit_loss,
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

    return render(request, 'webull_trader/day_analytics.html', {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "initial_date": today.strftime("%Y-%m-%d"),
        "profit_events": profit_events,
        "loss_events": loss_events,
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
    day_profit_loss = utils.get_day_profit_loss_for_render(acc_stat)
    # top gain & loss
    day_top_gain = {
        "value": "+${}".format(daytrade_perf.top_gain_amount),
        "symbol": daytrade_perf.top_gain_symbol
    }
    day_top_loss = {
        "value": "-${}".format(abs(daytrade_perf.top_loss_amount)),
        "symbol": daytrade_perf.top_loss_symbol
    }

    buy_orders, sell_orders = utils.get_day_trade_orders(date=acc_stat.date)
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    hourly_statistics = utils.get_stats_empty_list(size=32)
    # for hourly P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        hourly_idx = utils.get_market_hourly_interval_index(
            utils.local_datetime(day_trade['buy_time']))
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
    trades_dist = utils.get_trade_stat_dist_from_trades(day_trades)
    # trade records
    trade_records = []
    for symbol, trade in trades_dist.items():
        trade_record_for_render = utils.get_trade_stat_record_for_render(
            symbol, trade, date)
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
    minute_bars = get_list_or_404(
        HistoricalMinuteBar, date=date, symbol=symbol)

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
    m2_bars['ema9'] = m2_bars['close'].ewm(span=9, adjust=False).mean()
    # load 2m data for render
    m2_candle_data = utils.get_minute_candle_data_for_render(m2_bars)
    # calculate 5m bars
    m5_bars = utils.convert_5m_bars(m1_bars)
    # calculate and fill ema 9 data
    m5_bars['ema9'] = m5_bars['close'].ewm(span=9, adjust=False).mean()
    # load 5m data for render
    m5_candle_data = utils.get_minute_candle_data_for_render(m5_bars)
    # borrow minute bar for date
    analytics_date = minute_bars[0].date
    # calculate daily candle
    d1_candle_data = utils.get_last_60d_daily_candle_data_for_render(
        symbol, analytics_date)
    # 1m trade records
    m1_trade_price_records = []
    m1_trade_quantity_records = []
    # 2m trade records
    m2_trade_price_records = []
    m2_trade_quantity_records = []

    buy_orders, sell_orders = utils.get_day_trade_orders(
        date=analytics_date, symbol=symbol)
    for buy_order in buy_orders:
        m1_coord = [
            utils.local_time_minute_delay(buy_order.filled_time),
            # use high price avoid block candle
            utils.get_minute_candle_high_by_time_minute(
                m1_candle_data, utils.local_time_minute_delay(buy_order.filled_time)) + 0.01,
        ]
        m1_trade_price_records.append({
            "name": "{}".format(buy_order.avg_price),
            "coord": m1_coord,
            "value": buy_order.avg_price,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
        m1_trade_quantity_records.append({
            "name": "+{}".format(buy_order.filled_quantity),
            "coord": m1_coord,
            "value": buy_order.avg_price,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
        m2_coord = [
            utils.local_time_minute2(buy_order.filled_time),
            # use high price avoid block candle
            utils.get_minute_candle_high_by_time_minute(
                m2_candle_data, utils.local_time_minute2(buy_order.filled_time)) + 0.01,
        ]
        m2_trade_price_records.append({
            "name": "{}".format(buy_order.avg_price),
            "coord": m2_coord,
            "value": buy_order.avg_price,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
        m2_trade_quantity_records.append({
            "name": "+{}".format(buy_order.filled_quantity),
            "coord": m2_coord,
            "value": buy_order.avg_price,
            "itemStyle": {"color": config.BUY_COLOR},
            "label": {"fontSize": 10},
        })
    for sell_order in sell_orders:
        m1_coord = [
            utils.local_time_minute_delay(sell_order.filled_time),
            # use high price avoid block candle
            utils.get_minute_candle_high_by_time_minute(
                m1_candle_data, utils.local_time_minute_delay(sell_order.filled_time)) + 0.01,
        ]
        m1_trade_price_records.append({
            "name": "{}".format(sell_order.avg_price),
            "coord": m1_coord,
            "value": sell_order.avg_price,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })
        m1_trade_quantity_records.append({
            "name": "-{}".format(sell_order.filled_quantity),
            "coord": m1_coord,
            "value": sell_order.avg_price,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })
        m2_coord = [
            utils.local_time_minute2(sell_order.filled_time),
            # use high price avoid block candle
            utils.get_minute_candle_high_by_time_minute(
                m2_candle_data, utils.local_time_minute2(sell_order.filled_time)) + 0.01,
        ]
        m2_trade_price_records.append({
            "name": "{}".format(sell_order.avg_price),
            "coord": m2_coord,
            "value": sell_order.avg_price,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })
        m2_trade_quantity_records.append({
            "name": "-{}".format(sell_order.filled_quantity),
            "coord": m2_coord,
            "value": sell_order.avg_price,
            "itemStyle": {"color": config.SELL_COLOR},
            "label": {"fontSize": 10},
        })
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    trade_records = []
    for day_trade in day_trades:
        buy_price = day_trade["buy_price"]
        if "sell_price" in day_trade:
            sell_price = day_trade["sell_price"]
            quantity = day_trade["quantity"]
            gain = round((sell_price - buy_price) * quantity, 2)
            profit_loss, profit_loss_style = utils.get_color_profit_loss_style_for_render(
                gain)

            setup = None
            buy_order_notes = WebullOrderNote.objects.filter(
                order_id=day_trade["buy_order_id"])
            if len(buy_order_notes) > 0:
                setup = SetupType.tostr(buy_order_notes[0].setup)
            notes = []
            sell_order_notes = WebullOrderNote.objects.filter(
                order_id=day_trade["sell_order_id"])
            for sell_order_note in sell_order_notes:
                notes.append(sell_order_note.note)
            trade_records.append({
                "symbol": symbol,
                "quantity": quantity,
                "total_cost": "${}".format(round(quantity * buy_price, 2)),
                "buy_price": "${}".format(buy_price),
                "sell_price": "${}".format(sell_price),
                "buy_time": utils.local_time_minute_second(day_trade["buy_time"]),
                "sell_time": utils.local_time_minute_second(day_trade["sell_time"]),
                "setup": setup,
                "notes": " ".join(notes),
                "profit_loss": profit_loss,
                "profit_loss_style": profit_loss_style,
            })
    # stats
    trades_dist = utils.get_trade_stat_dist_from_trades(day_trades)
    trade_stats = utils.get_trade_stat_record_for_render(
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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    price_statistics = utils.get_stats_empty_list(size=16)
    # for price range P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        price_idx = utils.get_entry_price_range_index(day_trade['buy_price'])
        if 'sell_price' in day_trade:
            gain = (day_trade['sell_price'] -
                    day_trade['buy_price']) * day_trade['quantity']
            if gain > 0:
                price_statistics[price_idx]['win_trades'] += 1
                price_statistics[price_idx]['total_profit'] += gain
            else:
                price_statistics[price_idx]['loss_trades'] += 1
                price_statistics[price_idx]['total_loss'] += gain
            price_statistics[price_idx]['profit_loss'] += gain
            price_statistics[price_idx]['trades'] += 1
    price_profit_loss = []
    price_win_rate = []
    price_profit_loss_ratio = []
    price_trades = []
    # calculate win rate and profit/loss ratio
    for price_stat in price_statistics:
        price_trades.append(price_stat['trades'])
        price_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(price_stat['profit_loss'], 2)))
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
        "win_rate": price_win_rate,
        "profit_loss_ratio": price_profit_loss_ratio,
        "trades": price_trades,
    }

    cache.set('day_reports_price_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
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
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_mktcap_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
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
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_float_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
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
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_turnover_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
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
        "win_rate": stat_render['win_rate'],
        "profit_loss_ratio": stat_render['profit_loss_ratio'],
        "trades": stat_render['trades'],
    }

    cache.set('day_reports_short_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    gap_statistics = utils.get_stats_empty_list(
        size=len(utils.get_gap_range_labels()))
    # for P&L, win rate and profit/loss ratio, trades by gap
    for day_trade in day_trades:
        gap = utils.get_gap_by_symbol_date(
            day_trade['symbol'], day_trade['buy_time'].date())
        gap_idx = utils.get_gap_range_index(gap)
        if 'sell_price' in day_trade:
            gain = (day_trade['sell_price'] -
                    day_trade['buy_price']) * day_trade['quantity']
            if gain > 0:
                gap_statistics[gap_idx]['win_trades'] += 1
                gap_statistics[gap_idx]['total_profit'] += gain
            else:
                gap_statistics[gap_idx]['loss_trades'] += 1
                gap_statistics[gap_idx]['total_loss'] += gain
            gap_statistics[gap_idx]['profit_loss'] += gain
            gap_statistics[gap_idx]['trades'] += 1
    gap_profit_loss = []
    gap_win_rate = []
    gap_profit_loss_ratio = []
    gap_trades = []
    # calculate win rate and profit/loss ratio
    for gap_stat in gap_statistics:
        gap_trades.append(gap_stat['trades'])
        gap_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(gap_stat['profit_loss'], 2)))
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
        "win_rate": gap_win_rate,
        "profit_loss_ratio": gap_profit_loss_ratio,
        "trades": gap_trades,
    }

    cache.set('day_reports_gap_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    relvol_statistics = utils.get_stats_empty_list(
        size=len(utils.get_relative_volume_labels()))
    # for P&L, win rate and profit/loss ratio, trades by relative volume
    for day_trade in day_trades:
        symbol = day_trade['symbol']
        buy_date = day_trade['buy_time'].date()
        key_statistics = utils.get_hist_key_stat(symbol, buy_date)
        if key_statistics:
            relative_volume = round(
                key_statistics.volume / key_statistics.avg_vol_3m, 2)
            relvol_idx = utils.get_relative_volume_index(relative_volume)
            if 'sell_price' in day_trade:
                gain = (day_trade['sell_price'] -
                        day_trade['buy_price']) * day_trade['quantity']
                if gain > 0:
                    relvol_statistics[relvol_idx]['win_trades'] += 1
                    relvol_statistics[relvol_idx]['total_profit'] += gain
                else:
                    relvol_statistics[relvol_idx]['loss_trades'] += 1
                    relvol_statistics[relvol_idx]['total_loss'] += gain
                relvol_statistics[relvol_idx]['profit_loss'] += gain
                relvol_statistics[relvol_idx]['trades'] += 1
    relvol_profit_loss = []
    relvol_win_rate = []
    relvol_profit_loss_ratio = []
    relvol_trades = []
    # calculate win rate and profit/loss ratio
    for relvol_stat in relvol_statistics:
        relvol_trades.append(relvol_stat['trades'])
        relvol_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(relvol_stat['profit_loss'], 2)))
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
        "win_rate": relvol_win_rate,
        "profit_loss_ratio": relvol_profit_loss_ratio,
        "trades": relvol_trades,
    }

    cache.set('day_reports_relvol_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    holding_statistics = utils.get_stats_empty_list(
        size=len(utils.get_holding_time_labels()))
    # for P&L, win rate and profit/loss ratio, trades by holding time
    for day_trade in day_trades:
        if 'sell_price' in day_trade:
            holding_sec = (day_trade['sell_time'] -
                           day_trade['buy_time']).seconds
            holding_idx = utils.get_holding_time_index(holding_sec)
            gain = (day_trade['sell_price'] -
                    day_trade['buy_price']) * day_trade['quantity']
            if gain > 0:
                holding_statistics[holding_idx]['win_trades'] += 1
                holding_statistics[holding_idx]['total_profit'] += gain
            else:
                holding_statistics[holding_idx]['loss_trades'] += 1
                holding_statistics[holding_idx]['total_loss'] += gain
            holding_statistics[holding_idx]['profit_loss'] += gain
            holding_statistics[holding_idx]['trades'] += 1
    holding_profit_loss = []
    holding_win_rate = []
    holding_profit_loss_ratio = []
    holding_trades = []
    # calculate win rate and profit/loss ratio
    for holding_stat in holding_statistics:
        holding_trades.append(holding_stat['trades'])
        holding_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(holding_stat['profit_loss'], 2)))
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
        "win_rate": holding_win_rate,
        "profit_loss_ratio": holding_profit_loss_ratio,
        "trades": holding_trades,
    }

    cache.set('day_reports_holding_cache', context, CACHE_TIMEOUT)

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

    buy_orders, sell_orders = utils.get_day_trade_orders()
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
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

    cache.set('day_reports_hourly_cache', context, CACHE_TIMEOUT)

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
        "title": "Hourly",
        "daily_labels": daily_labels,
        "daily_profit_loss": daily_profit_loss,
        "daily_win_rate": daily_win_rate,
        "daily_profit_loss_ratio": daily_profit_loss_ratio,
        "daily_trades": daily_trades,
    }

    cache.set('day_reports_daily_cache', context, CACHE_TIMEOUT)

    return render(request, 'webull_trader/day_reports_daily.html', context)


@login_required
def swing_positions(request):

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    positions = SwingPosition.objects.all()
    last_acc_stat = WebullAccountStatistics.objects.last()
    net_liquidation = last_acc_stat.net_liquidation

    swing_positions = []
    for position in positions:
        symbol = position.symbol
        setup = SetupType.tostr(position.setup)
        buy_date = position.buy_date
        unit_cost = position.cost
        quantity = position.quantity
        total_cost = unit_cost * quantity

        last_price = 0.0
        last_bar = SwingHistoricalDailyBar.objects.filter(symbol=symbol).last()
        if last_bar:
            last_price = last_bar.close

        total_value = last_price * quantity

        portfolio_percent = total_value / net_liquidation

        unrealized_pl = total_value - total_cost
        unrealized_pl_percent = (total_value - total_cost) / total_cost

        profit_loss, profit_loss_style = utils.get_color_profit_loss_style_for_render(
            round(unrealized_pl, 2))

        swing_positions.append({
            "symbol": symbol,
            "unit_cost": "${}".format(unit_cost),
            "total_cost": "${}".format(round(total_cost, 2)),
            "total_value": "${}".format(round(total_value, 2)),
            "quantity": quantity,
            "buy_date": buy_date,
            "setup": setup,
            "price": "${}".format(last_price),
            "profit_loss": profit_loss,
            "profit_loss_percent": "{}%".format(round(unrealized_pl_percent * 100, 2)),
            "profit_loss_style": profit_loss_style,
            "portfolio_percent": "{}%".format(round(portfolio_percent * 100, 2)),
        })

    context = {
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "swing_positions": swing_positions,
    }

    return render(request, 'webull_trader/swing_positions.html', context)


@login_required
def swing_positions_symbol(request, symbol=None):
    position = get_object_or_404(SwingPosition, symbol=symbol)
    watchlist = get_object_or_404(SwingWatchlist, symbol=symbol)
    daily_bars = get_list_or_404(SwingHistoricalDailyBar, symbol=symbol)
    print(daily_bars)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type_texts = utils.get_algo_type_texts()

    # fmp quote data
    quote = fmpsdk.get_quote(symbol)
    eps = None
    if quote["eps"]:
        eps = round(quote["eps"], 2)
    pe = None
    if quote["pe"]:
        pe = round(quote["pe"], 2)
    sector = None
    if watchlist.sector:
        sector = watchlist.sector
    next_earning = None
    # search next earning
    earnings = EarningCalendar.objects.filter(symbol=symbol)
    for earning in earnings:
        if earning.earning_date >= date.today():
            next_earning = "{} ({})".format(
                earning.earning_date, earning.earning_time)
    quote_data = {
        "market_value": utils.millify(quote["marketCap"]),
        "free_float": utils.millify(quote['sharesOutstanding']),
        "pe": pe,
        "eps": eps,
        "sector": sector,
        "next_earning": next_earning,
    }

    # swing position
    unit_cost = position.cost
    quantity = position.quantity
    total_cost = unit_cost * quantity
    last_price = quote['price']
    total_value = last_price * quantity
    last_acc_stat = WebullAccountStatistics.objects.last()
    net_liquidation = last_acc_stat.net_liquidation
    portfolio_percent = total_value / net_liquidation
    unrealized_pl = total_value - total_cost
    unrealized_pl_percent = (total_value - total_cost) / total_cost

    profit_loss, profit_loss_style = utils.get_color_profit_loss_style_for_render(
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
    }

    context = {
        "symbol": symbol,
        "account_type": account_type,
        "algo_type_texts": algo_type_texts,
        "quote": quote_data,
        "position": swing_position,
    }

    return render(request, 'webull_trader/swing_positions_symbol.html', context)
