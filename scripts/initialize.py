# -*- coding: utf-8 -*-

# initialize script

def start():
    from sdk import fmpsdk
    from common import db, utils
    from common.watchlist import WATCHLIST_SYMBOLS
    from webull_trader.models import SwingWatchlist

    db.get_or_create_trading_settings()
    print("[{}] Trading settings initialized successful.".format(utils.get_now()))

    for symbol in WATCHLIST_SYMBOLS:
        watchlist = SwingWatchlist.objects.filter(symbol=symbol).first()
        if not watchlist:
            watchlist = SwingWatchlist(symbol=symbol)
            print("[{}] Saving <{}> watchlist...".format(
                utils.get_now(), symbol))
        else:
            print("[{}] Updating <{}> watchlist...".format(
                utils.get_now(), symbol))
        # get profile from FMP
        profile = fmpsdk.get_profile(symbol)
        if profile:
            watchlist.sector = profile["sector"]
            watchlist.exchange = profile["exchangeShortName"]
            watchlist.is_etf = profile["isEtf"]
        watchlist.save()

    print("[{}] Swing watchlist initialized successful".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()
