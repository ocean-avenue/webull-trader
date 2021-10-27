# -*- coding: utf-8 -*-

# fetch stock quotes for swing trades


def start():
    from common import utils
    from webull_trader.models import SwingWatchlist

    algo_type = utils.get_algo_type()

    if utils.is_swing_trade_algo(algo_type):
        swing_watchlist = SwingWatchlist.objects.all()
        symbol_list = []
        for swing_watch in swing_watchlist:
            symbol_list.append(swing_watch.symbol)

        utils.fetch_stock_quotes(symbol_list)


if __name__ == "django.core.management.commands.shell":
    start()
