# -*- coding: utf-8 -*-

# fill miss historical statistics data

def start():
    from datetime import date
    from sdk import webullsdk
    from common import utils, db
    from webull_trader.models import WebullAccountStatistics, DayTrade, HistoricalMarketStatistics, HistoricalDayTradePerformance

    acc_stat_list = WebullAccountStatistics.objects.all()
    for acc_stat in acc_stat_list:
        day = acc_stat.date
        # day trades
        day_trades = DayTrade.objects.filter(
            sell_date=day, require_adjustment=False)
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
            overall_win_rate = round(
                total_win_trades / total_day_trades * 100, 2)
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
        if hist_daytrade_perf.trades > 0:
            hist_daytrade_perf.save()

        # market stat
        hist_market_stat = HistoricalMarketStatistics.objects.filter(
            date=day).first()
        if not hist_market_stat:
            hist_market_stat = HistoricalMarketStatistics(date=day)
        today = date.today()
        if ((day.weekday() == 4 or day.weekday() == 5 or day.weekday() == 6) and (today - day).days <= 3) or \
                (today - day).days == 0:
            top_gainer_change = utils.get_avg_change_from_movers(
                webullsdk.get_top_gainers(count=10))
            pre_gainer_change = utils.get_avg_change_from_movers(
                webullsdk.get_pre_market_gainers(count=10))
            after_gainer_change = utils.get_avg_change_from_movers(
                webullsdk.get_after_market_gainers(count=10))
            top_loser_change = utils.get_avg_change_from_movers(
                webullsdk.get_top_losers(count=10))
            pre_loser_change = utils.get_avg_change_from_movers(
                webullsdk.get_pre_market_losers(count=10))
            after_loser_change = utils.get_avg_change_from_movers(
                webullsdk.get_after_market_losers(count=10))
            db.save_hist_market_statistics({
                'top_gainer_change': top_gainer_change,
                'pre_gainer_change': pre_gainer_change,
                'after_gainer_change': after_gainer_change,
                'top_loser_change': top_loser_change,
                'pre_loser_change': pre_loser_change,
                'after_loser_change': after_loser_change,
            }, day)
        else:
            db.save_hist_market_statistics({
                'top_gainer_change': 0.0,
                'pre_gainer_change': 0.0,
                'after_gainer_change': 0.0,
                'top_loser_change': 0.0,
                'pre_loser_change': 0.0,
                'after_loser_change': 0.0,
            }, day)


if __name__ == "django.core.management.commands.shell":
    start()
