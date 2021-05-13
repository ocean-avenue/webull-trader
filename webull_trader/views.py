import pandas as pd
from datetime import date
from django.shortcuts import get_list_or_404, get_object_or_404, render
from scripts import utils, config
from webull_trader.enums import ActionType, OrderType, SetupType
from webull_trader.models import HistoricalDayTradePerformance, HistoricalKeyStatistics, HistoricalMinuteBar, WebullAccountStatistics, WebullNews, WebullOrder, WebullOrderNote

# Create your views here.


def index(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

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
        "algo_type": algo_type,
        "net_account_value": net_account_value,
        "day_profit_loss": day_profit_loss,
        "net_assets": net_assets,
        "profit_loss": profit_loss,
    })


def analytics(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

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
        event_url = "/analytics/{}".format(event_date)
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

    return render(request, 'webull_trader/analytics.html', {
        "account_type": account_type,
        "algo_type": algo_type,
        "initial_date": today.strftime("%Y-%m-%d"),
        "profit_events": profit_events,
        "loss_events": loss_events,
    })


def analytics_date(request, date=None):
    daytrade_perf = get_object_or_404(HistoricalDayTradePerformance, date=date)
    acc_stat = get_object_or_404(WebullAccountStatistics, date=date)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

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

    # only limit orders for day trades
    buy_orders = WebullOrder.objects.filter(filled_time__year=acc_stat.date.year, filled_time__month=acc_stat.date.month,
                                            filled_time__day=acc_stat.date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.BUY)
    sell_orders = WebullOrder.objects.filter(filled_time__year=acc_stat.date.year, filled_time__month=acc_stat.date.month,
                                             filled_time__day=acc_stat.date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.SELL)
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

    return render(request, 'webull_trader/analytics_date.html', {
        "account_type": account_type,
        "algo_type": algo_type,
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


def analytics_date_symbol(request, date=None, symbol=None):
    minute_bars = get_list_or_404(
        HistoricalMinuteBar, date=date, symbol=symbol)

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

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
    buy_orders = WebullOrder.objects.filter(filled_time__year=analytics_date.year, filled_time__month=analytics_date.month,
                                            filled_time__day=analytics_date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.BUY).filter(symbol=symbol)
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
    sell_orders = WebullOrder.objects.filter(filled_time__year=analytics_date.year, filled_time__month=analytics_date.month,
                                             filled_time__day=analytics_date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.SELL).filter(symbol=symbol)
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
            profit_loss_style = "text-success"
            profit_loss = "+${}".format(gain)
            if gain < 0:
                profit_loss = "-${}".format(abs(gain))
                profit_loss_style = "text-danger"
            entries = []
            buy_order_notes = WebullOrderNote.objects.filter(
                order_id=day_trade["buy_order_id"])
            for buy_order_note in buy_order_notes:
                entries.append(SetupType.tostr(buy_order_note.setup))
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
                "entry": ", ".join(entries),
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

    return render(request, 'webull_trader/analytics_date_symbol.html', {
        "date": date,
        "symbol": symbol,
        "account_type": account_type,
        "algo_type": algo_type,
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
    })


def reports_price(request):

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

    # only limit orders for day trades
    buy_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.BUY)
    sell_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.SELL)
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
        if price_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        price_profit_loss_ratio.append(profit_loss_ratio)

    return render(request, 'webull_trader/reports_price.html', {
        "account_type": account_type,
        "algo_type": algo_type,
        "price_labels": utils.get_entry_price_range_labels(),
        "price_profit_loss": price_profit_loss,
        "price_win_rate": price_win_rate,
        "price_profit_loss_ratio": price_profit_loss_ratio,
        "price_trades": price_trades,
    })


def reports_mktcap(request):

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

    # only limit orders for day trades
    buy_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.BUY)
    sell_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.SELL)
    # day trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    mktcap_statistics = utils.get_stats_empty_list(size=16)
    # for market cap range P&L, win rate and profit/loss ratio, trades
    for day_trade in day_trades:
        symbol = day_trade['symbol']
        buy_date = day_trade['buy_time'].date()
        key_statistics = HistoricalKeyStatistics.objects.filter(
            symbol=symbol).filter(date=buy_date).first()
        mktcap = key_statistics.market_value
        mktcap_idx = utils.get_market_cap_range_index(mktcap)
        if 'sell_price' in day_trade:
            gain = (day_trade['sell_price'] -
                    day_trade['buy_price']) * day_trade['quantity']
            if gain > 0:
                mktcap_statistics[mktcap_idx]['win_trades'] += 1
                mktcap_statistics[mktcap_idx]['total_profit'] += gain
            else:
                mktcap_statistics[mktcap_idx]['loss_trades'] += 1
                mktcap_statistics[mktcap_idx]['total_loss'] += gain
            mktcap_statistics[mktcap_idx]['profit_loss'] += gain
            mktcap_statistics[mktcap_idx]['trades'] += 1
    mktcap_profit_loss = []
    mktcap_win_rate = []
    mktcap_profit_loss_ratio = []
    mktcap_trades = []
    # calculate win rate and profit/loss ratio
    for mktcap_stat in mktcap_statistics:
        mktcap_trades.append(mktcap_stat['trades'])
        mktcap_profit_loss.append(utils.get_color_bar_chart_item_for_render(
            round(mktcap_stat['profit_loss'], 2)))
        if mktcap_stat['trades'] > 0:
            mktcap_win_rate.append(
                round(mktcap_stat['win_trades']/mktcap_stat['trades'] * 100, 2))
        else:
            mktcap_win_rate.append(0.0)
        avg_profit = 1.0
        if mktcap_stat['win_trades'] > 0:
            avg_profit = mktcap_stat['total_profit'] / \
                mktcap_stat['win_trades']
        avg_loss = 1.0
        if mktcap_stat['loss_trades'] > 0:
            avg_loss = mktcap_stat['total_loss'] / mktcap_stat['loss_trades']
        profit_loss_ratio = 0.0
        if mktcap_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        mktcap_profit_loss_ratio.append(profit_loss_ratio)

    return render(request, 'webull_trader/reports_mktcap.html', {
        "account_type": account_type,
        "algo_type": algo_type,
        "mktcap_labels": utils.get_market_cap_range_labels(),
        "mktcap_profit_loss": mktcap_profit_loss,
        "mktcap_win_rate": mktcap_win_rate,
        "mktcap_profit_loss_ratio": mktcap_profit_loss_ratio,
        "mktcap_trades": mktcap_trades,
    })


def reports_hourly(request):

    # account type data
    account_type = utils.get_account_type_for_render()

    # algo type data
    algo_type = utils.get_algo_type_description()

    # only limit orders for day trades
    buy_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.BUY)
    sell_orders = WebullOrder.objects.filter(order_type=OrderType.LMT).filter(
        status="Filled").filter(action=ActionType.SELL)
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
        if hourly_stat['trades'] > 0 and avg_loss < 0:
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        hourly_profit_loss_ratio.append(profit_loss_ratio)

    return render(request, 'webull_trader/reports_hourly.html', {
        "account_type": account_type,
        "algo_type": algo_type,
        "hourly_labels": utils.get_market_hourly_interval_labels(),
        "hourly_profit_loss": hourly_profit_loss,
        "hourly_win_rate": hourly_win_rate,
        "hourly_profit_loss_ratio": hourly_profit_loss_ratio,
        "hourly_trades": hourly_trades,
    })
