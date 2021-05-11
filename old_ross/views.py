import pandas as pd
from datetime import datetime, date
from django.shortcuts import get_list_or_404, get_object_or_404, render
from scripts import utils, config
from old_ross.enums import ActionType, OrderType, SetupType
from old_ross.models import HistoricalDailyBar, HistoricalDayTradePerformance, HistoricalKeyStatistics, HistoricalMinuteBar, WebullAccountStatistics, WebullNews, WebullOrder, WebullOrderNote

# Create your views here.


def index(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

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

    return render(request, 'old_ross/index.html', {
        "account_type": account_type,
        "net_account_value": net_account_value,
        "day_profit_loss": day_profit_loss,
        "net_assets": net_assets,
        "profit_loss": profit_loss,
    })


def analytics(request):
    today = date.today()

    # account type data
    account_type = utils.get_account_type_for_render()

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

    return render(request, 'old_ross/analytics.html', {
        "account_type": account_type,
        "initial_date": today.strftime("%Y-%m-%d"),
        "profit_events": profit_events,
        "loss_events": loss_events,
    })


def analytics_date(request, date=None):
    daytrade_perf = get_object_or_404(HistoricalDayTradePerformance, date=date)
    acc_stat = get_object_or_404(WebullAccountStatistics, date=date)

    # account type data
    account_type = utils.get_account_type_for_render()

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
    hourly_statistics = utils.get_market_hourly_interval_empty()
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
            profit_loss_ratio = round(abs(avg_profit/avg_loss), 2)
        hourly_profit_loss_ratio.append(profit_loss_ratio)

    # for trade records group by symbol
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
    # trade records
    trade_records = []
    for symbol, trade in trades_dist.items():
        key_statistics = HistoricalKeyStatistics.objects.filter(
            symbol=symbol).filter(date=date).first()
        mktcap = 0
        short_float = None
        float_shares = 0
        turnover_rate = "0.0%"
        relative_volume = 0
        if key_statistics:
            mktcap = utils.millify(key_statistics.market_value)
            if key_statistics.short_float:
                short_float = "{}%".format(key_statistics.short_float)
            float_shares = utils.millify(key_statistics.outstanding_shares)
            turnover_rate = "{}%".format(
                round(key_statistics.turnover_rate * 100, 2))
            relative_volume = round(
                key_statistics.volume / key_statistics.avg_vol_3m, 2)
        win_rate = "0.0%"
        if trade["trades"] > 0:
            win_rate = "{}%".format(
                round(trade["win_trades"] / trade["trades"] * 100, 2))
        avg_profit = 0.0
        if trade["win_trades"] > 0:
            avg_profit = trade["total_gain"] / trade["win_trades"]
        avg_loss = 0.0
        if trade["loss_trades"] > 0:
            avg_loss = abs(trade["total_loss"] / trade["loss_trades"])
        profit_loss_ratio = 1.0
        if avg_loss > 0:
            profit_loss_ratio = round(avg_profit/avg_loss, 2)
        avg_price = "${}".format(
            round(trade["total_cost"] / trade["trades"], 2))
        profit_loss = "+${}".format(round(trade["profit_loss"], 2))
        profit_loss_style = "text-success"
        if trade["profit_loss"] < 0:
            profit_loss = "-${}".format(abs(round(trade["profit_loss"], 2)))
            profit_loss_style = "text-danger"
        hist_daily_bars = HistoricalDailyBar.objects.filter(symbol=symbol)
        day_index = 0
        for i in range(0, len(hist_daily_bars)):
            if hist_daily_bars[i].date == key_statistics.date:
                day_index = i
                break
        gap = "0.0%"
        if day_index > 0:
            gap_value = round((hist_daily_bars[day_index].open - hist_daily_bars[day_index -
                                                                                 1].close) / hist_daily_bars[day_index - 1].close * 100, 2)
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
        trade_records.append({
            "symbol": symbol,
            "trades": trade["trades"],
            "profit_loss_value": round(trade["profit_loss"], 2),
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
        })
    # sort trade records
    trade_records.sort(key=lambda t: t['profit_loss_value'], reverse=True)

    return render(request, 'old_ross/analytics_date.html', {
        "account_type": account_type,
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
    # borrow minute bar for date
    analytics_date = minute_bars[0].date
    # calculate daily candle
    d1_candle_data = utils.get_last_60d_daily_candle_data_for_render(
        symbol, analytics_date)
    # 1m trade records
    m1_trade_records = []
    # 2m trade records
    m2_trade_records = []
    buy_orders = WebullOrder.objects.filter(filled_time__year=analytics_date.year, filled_time__month=analytics_date.month,
                                            filled_time__day=analytics_date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.BUY).filter(symbol=symbol)
    for buy_order in buy_orders:
        m1_trade_records.append({
            # "name": "+{}".format(buy_order.filled_quantity),
            "name": "{}".format(buy_order.avg_price),
            "coord": [
                utils.local_time_minute_delay(buy_order.filled_time),
                buy_order.avg_price * 1.04
            ],
            "value": buy_order.avg_price,
            "itemStyle": {
                "color": config.BUY_COLOR,
            }
        })
        m2_trade_records.append({
            # "name": "+{}".format(buy_order.filled_quantity),
            "name": "{}".format(buy_order.avg_price),
            "coord": [
                utils.local_time_minute2(buy_order.filled_time),
                buy_order.avg_price * 1.04
            ],
            "value": buy_order.avg_price,
            "itemStyle": {
                "color": config.BUY_COLOR,
            }
        })
    sell_orders = WebullOrder.objects.filter(filled_time__year=analytics_date.year, filled_time__month=analytics_date.month,
                                             filled_time__day=analytics_date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.SELL).filter(symbol=symbol)
    for sell_order in sell_orders:
        m1_trade_records.append({
            # "name": "-{}".format(sell_order.filled_quantity),
            "name": "{}".format(sell_order.avg_price),
            "coord": [
                utils.local_time_minute_delay(sell_order.filled_time),
                sell_order.avg_price * 1.04
            ],
            "value": sell_order.avg_price,
            "itemStyle": {
                "color": config.SELL_COLOR,
            }
        })
        m2_trade_records.append({
            # "name": "-{}".format(sell_order.filled_quantity),
            "name": "{}".format(sell_order.avg_price),
            "coord": [
                utils.local_time_minute2(sell_order.filled_time),
                sell_order.avg_price * 1.04
            ],
            "value": sell_order.avg_price,
            "itemStyle": {
                "color": config.SELL_COLOR,
            }
        })
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    trade_records = []
    for day_trade in day_trades:
        buy_price = day_trade["buy_price"]
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
            "buy_price": "${}".format(buy_price),
            "sell_price": "${}".format(sell_price),
            "buy_time": utils.local_time_minute_second(day_trade["buy_time"]),
            "sell_time": utils.local_time_minute_second(day_trade["sell_time"]),
            "entry": ", ".join(entries),
            "notes": " ".join(notes),
            "profit_loss": profit_loss,
            "profit_loss_style": profit_loss_style,
        })

    return render(request, 'old_ross/analytics_date_symbol.html', {
        "date": date,
        "symbol": symbol,
        "m1_candle_data": m1_candle_data,
        "m2_candle_data": m2_candle_data,
        "m1_trade_records": m1_trade_records,
        "m2_trade_records": m2_trade_records,
        "d1_candle_data": d1_candle_data,
        "trade_records": trade_records,
    })
