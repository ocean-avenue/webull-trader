from datetime import datetime, date
from django.shortcuts import get_object_or_404, render
from scripts import utils, config
from old_ross.enums import ActionType, OrderType
from old_ross.models import HistoricalDailyBar, HistoricalDayTradePerformance, HistoricalKeyStatistics, WebullAccountStatistics, WebullNews, WebullOrder

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

    last_acc_status = WebullAccountStatistics.objects.last()
    if last_acc_status:
        net_account_value["value"] = "${}".format(
            last_acc_status.net_liquidation)

        net_account_value["total_pl"] = "{}".format(
            last_acc_status.total_profit_loss)
        if last_acc_status.total_profit_loss > 0:
            net_account_value["total_pl"] = "+" + net_account_value["total_pl"]
            net_account_value["total_pl_style"] = "badge-soft-success"
        elif last_acc_status.total_profit_loss < 0:
            net_account_value["total_pl_style"] = "badge-soft-danger"

        net_account_value["total_pl_rate"] = "{}%".format(
            last_acc_status.total_profit_loss_rate * 100)
        if last_acc_status.total_profit_loss_rate > 0:
            net_account_value["total_pl_rate"] = "+" + \
                net_account_value["total_pl_rate"]
            net_account_value["total_pl_rate_style"] = "badge-soft-success"
        elif last_acc_status.total_profit_loss_rate < 0:
            net_account_value["total_pl_rate_style"] = "badge-soft-danger"

    today_acc_status = WebullAccountStatistics.objects.filter(
        date=today).first()
    day_profit_loss = utils.get_day_profit_loss_for_render(today_acc_status)

    acc_status_list = WebullAccountStatistics.objects.all()
    # net assets chart
    net_assets_daily_values = []
    net_assets_daily_dates = []
    # profit loss chart
    profit_loss_daily_values = []
    profit_loss_daily_dates = []

    for acc_status in acc_status_list:
        net_assets_daily_values.append(acc_status.net_liquidation)
        net_assets_daily_dates.append(acc_status.date.strftime("%Y/%m/%d"))
        profit_loss_daily_values.append(
            utils.get_color_bar_chart_item_for_render(acc_status.day_profit_loss))
        profit_loss_daily_dates.append(acc_status.date.strftime("%Y/%m/%d"))

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
    acc_status = get_object_or_404(WebullAccountStatistics, date=date)

    # account type data
    account_type = utils.get_account_type_for_render()

    # day profit loss
    day_profit_loss = utils.get_day_profit_loss_for_render(acc_status)
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
    buy_orders = WebullOrder.objects.filter(filled_time__year=acc_status.date.year, filled_time__month=acc_status.date.month,
                                            filled_time__day=acc_status.date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.BUY)
    sell_orders = WebullOrder.objects.filter(filled_time__year=acc_status.date.year, filled_time__month=acc_status.date.month,
                                             filled_time__day=acc_status.date.day).filter(order_type=OrderType.LMT).filter(action=ActionType.SELL)
    # trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    # for trade records
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
        if key_statistics:
            mktcap = utils.millify(key_statistics.market_value)
            if key_statistics.short_float:
                short_float = "{}%".format(key_statistics.short_float)
            float_shares = utils.millify(key_statistics.outstanding_shares)
            turnover_rate = "{}%".format(round(key_statistics.turnover_rate * 100, 2))
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
            if datetime.strptime(webull_new.news_time, "%Y-%m-%dT%H:%M:%S.000+0000").date() == key_statistics.date:
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
        "trade_records": trade_records,
    })
