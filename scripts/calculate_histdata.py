# -*- coding: utf-8 -*-

# calculate historical statistics data

def start():
    from datetime import date
    from scripts import utils
    from webull_trader.models import HistoricalDayTradePerformance

    today = date.today()
    # day trade
    buy_orders, sell_orders = utils.get_day_trade_orders(date=today)
    # trades
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)
    # trade count
    total_day_trades = len(day_trades)
    # top gain & loss
    top_gain_amount = 0.0
    top_gain_symbol = ""
    top_loss_amount = 0.0
    top_loss_symbol = ""
    # win rate
    total_win_trades = 0
    total_loss_trades = 0
    # profit/loss ratio
    total_profit = 0.0
    total_loss = 0.0
    # day profit loss
    day_profit_loss = 0.0
    total_buy_amount = 0.0
    total_sell_amount = 0.0
    for order in buy_orders:
        total_buy_amount += (order.avg_price * order.filled_quantity)
    for order in sell_orders:
        total_sell_amount += (order.avg_price * order.filled_quantity)
    day_profit_loss = total_sell_amount - total_buy_amount
    # trade records
    trades_dist = {}
    for trade in day_trades:
        if "sell_price" in trade:
            symbol = trade["symbol"]
            gain = round(
                (trade["sell_price"] - trade["buy_price"]) * trade["quantity"], 2)
            # calculate win rate, profit/loss ratio
            if gain > 0:
                total_profit += gain
                total_win_trades += 1
            else:
                total_loss += gain
                total_loss_trades += 1
            # calculate top gain & loss
            if gain > top_gain_amount:
                top_gain_symbol = symbol
                top_gain_amount = gain
            if gain < top_loss_amount:
                top_loss_symbol = symbol
                top_loss_amount = gain
            # calculate day profit loss
            # day_profit_loss += gain
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
    # win rate
    overall_win_rate = 0.0
    if total_day_trades > 0:
        overall_win_rate = round(total_win_trades / total_day_trades * 100, 2)
    # profit/loss ratio
    overall_avg_profit = 0.0
    if total_win_trades > 0:
        overall_avg_profit = total_profit / total_win_trades
    overall_avg_loss = 0.0
    if total_loss_trades > 0:
        overall_avg_loss = abs(total_loss / total_loss_trades)
    overall_profit_loss_ratio = 1.0
    if overall_avg_loss > 0:
        overall_profit_loss_ratio = round(
            overall_avg_profit/overall_avg_loss, 2)

    # save hist daytrade perf object
    hist_daytrade_perf = HistoricalDayTradePerformance.objects.filter(
        date=today).first()
    if not hist_daytrade_perf:
        hist_daytrade_perf = HistoricalDayTradePerformance()
    hist_daytrade_perf.date = today
    hist_daytrade_perf.win_rate = overall_win_rate
    hist_daytrade_perf.profit_loss_ratio = overall_profit_loss_ratio
    hist_daytrade_perf.day_profit_loss = round(day_profit_loss, 2)
    hist_daytrade_perf.trades = total_day_trades
    hist_daytrade_perf.top_gain_amount = top_gain_amount
    hist_daytrade_perf.top_gain_symbol = top_gain_symbol
    hist_daytrade_perf.top_loss_amount = top_loss_amount
    hist_daytrade_perf.top_loss_symbol = top_loss_symbol
    hist_daytrade_perf.save()


if __name__ == "django.core.management.commands.shell":
    start()
