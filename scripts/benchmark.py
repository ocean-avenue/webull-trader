# -*- coding: utf-8 -*-

# fetch stock quotes for swing trades


def start():
    import sys
    from django.utils import timezone
    from common import utils, db
    from webull_trader.models import DayTrade

    def _progressbar(it, prefix="", size=60, file=sys.stdout):
        count = len(it)

        def show(j):
            x = int(size*j/count)
            file.write("%s[%s%s] %i/%i\r" %
                       (prefix, "#"*x, "."*(size-x), j, count))
            file.flush()
        show(0)
        for i, item in enumerate(it):
            yield item
            show(i+1)
        file.write("\n")
        file.flush()

    def _get_perf(trades):
        total_cost = 0.0
        total_sold = 0.0
        for trade in trades:
            trade: DayTrade = trade
            total_cost += trade.total_cost
            total_sold += trade.total_sold
        return f"{round((total_sold - total_cost) / total_cost * 100, 2)}%, ${round(total_sold - total_cost, 2)}"

    # performance benchmark
    all_trades = DayTrade.objects.all()
    print(f"Benchmark: {_get_perf(all_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 100000:
            filter_trades.append(trade)
    print(f"Volume > 100000 (regular): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 150000:
            filter_trades.append(trade)
    print(f"Volume > 150000 (regular): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 200000:
            filter_trades.append(trade)
    print(f"Volume > 200000 (regular): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 500000:
            filter_trades.append(trade)
    print(f"Volume > 500000 (regular): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 1000000:
            filter_trades.append(trade)
    print(f"Volume > 1000000 (regular): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip pre/after market
        if utils.is_after_market_time(buy_time) or utils.is_pre_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 1500000:
            filter_trades.append(trade)
    print(f"Volume > 1500000 (regular): {_get_perf(filter_trades)}")

    print()

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 10000:
            filter_trades.append(trade)
    print(f"Volume > 10000 (pre/after): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 15000:
            filter_trades.append(trade)
    print(f"Volume > 15000 (pre/after): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 20000:
            filter_trades.append(trade)
    print(f"Volume > 20000 (pre/after): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 50000:
            filter_trades.append(trade)
    print(f"Volume > 50000 (pre/after): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 100000:
            filter_trades.append(trade)
    print(f"Volume > 100000 (pre/after): {_get_perf(filter_trades)}")

    # filter out low volume trade
    filter_trades = []
    for trade in _progressbar(all_trades, "Computing: ", 60):
        trade: DayTrade = trade
        buy_time = trade.buy_time.astimezone(timezone.get_current_timezone())

        # skip regular market
        if utils.is_regular_market_time(buy_time):
            continue

        buy_bar = db.get_hist_minute_bar(trade.symbol, buy_time)
        if not buy_bar:
            continue
        if buy_bar.volume > 150000:
            filter_trades.append(trade)
    print(f"Volume > 150000 (pre/after): {_get_perf(filter_trades)}")


if __name__ == "django.core.management.commands.shell":
    start()
