# -*- coding: utf-8 -*-

# calculate historical statistics data

def start(day=None):
    from datetime import date
    from webull_trader.models import HistoricalDayTradePerformance, HistoricalSwingTradePerformance, DayTrade, SwingTrade

    if day == None:
        day = date.today()
    # trades
    day_trades = DayTrade.objects.filter(sell_date=day)
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
    day_total_buy_amount = 0.0
    day_total_sell_amount = 0.0
    # for order in buy_orders:
    #     day_total_buy_amount += (order.avg_price * order.filled_quantity)
    # for order in sell_orders:
    #     day_total_sell_amount += (order.avg_price * order.filled_quantity)
    # day_profit_loss = day_total_sell_amount - day_total_buy_amount
    # trade records
    for trade in day_trades:
        symbol = trade.symbol
        gain = round(trade.total_sold - trade.total_cost, 2)
        day_total_buy_amount += trade.total_cost
        day_total_sell_amount += trade.total_sold
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
        day_profit_loss += gain

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
        date=day).first()
    if not hist_daytrade_perf:
        hist_daytrade_perf = HistoricalDayTradePerformance(date=day)
    hist_daytrade_perf.win_rate = overall_win_rate
    hist_daytrade_perf.profit_loss_ratio = overall_profit_loss_ratio
    hist_daytrade_perf.day_profit_loss = round(day_profit_loss, 2)
    hist_daytrade_perf.trades = total_day_trades
    hist_daytrade_perf.top_gain_amount = top_gain_amount
    hist_daytrade_perf.top_gain_symbol = top_gain_symbol
    hist_daytrade_perf.top_loss_amount = top_loss_amount
    hist_daytrade_perf.top_loss_symbol = top_loss_symbol
    hist_daytrade_perf.total_buy_amount = round(day_total_buy_amount, 2)
    hist_daytrade_perf.total_sell_amount = round(day_total_sell_amount, 2)
    hist_daytrade_perf.save()

    # swing trades
    swing_trades = SwingTrade.objects.filter(sell_date=day)
    # swing profit loss
    swing_profit_loss = 0.0
    swing_total_buy_amount = 0.0
    swing_total_sell_amount = 0.0
    for trade in swing_trades:
        swing_total_buy_amount += trade.total_cost
        swing_total_sell_amount += trade.total_sold
    swing_profit_loss = swing_total_sell_amount - swing_total_buy_amount
    # save hist swingtrade perf object
    hist_swingtrade_perf = HistoricalSwingTradePerformance.objects.filter(
        date=day).first()
    if not hist_swingtrade_perf:
        hist_swingtrade_perf = HistoricalSwingTradePerformance(date=day)
    hist_swingtrade_perf.day_profit_loss = round(swing_profit_loss, 2)
    hist_swingtrade_perf.trades = len(swing_trades)
    hist_swingtrade_perf.total_buy_amount = round(swing_total_buy_amount, 2)
    hist_swingtrade_perf.total_sell_amount = round(swing_total_sell_amount, 2)
    hist_swingtrade_perf.save()


if __name__ == "django.core.management.commands.shell":
    start()
