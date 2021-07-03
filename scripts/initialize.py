# -*- coding: utf-8 -*-

# initialize script

def start():
    from scripts import utils
    from scripts.SWING_WATCHLIST import WATCHLIST_SYMBOLS
    from sdk import fmpsdk
    from webull_trader import enums
    from webull_trader.models import TradingSettings, SwingWatchlist

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        trading_settings = TradingSettings(
            paper=True,
            algo_type=enums.AlgorithmType.DAY_BREAKOUT_20,
            order_amount_limit=1000.0,
            extended_order_amount_limit=1000.0,
            target_profit_ratio=0.02,
            stop_loss_ratio=-0.01,
            day_free_float_limit_in_million=-1.0, # all free float
            day_sectors_limit='', # all sectors
            swing_position_amount_limit=1000.0,
            day_trade_usable_cash_threshold=10000.0,
        )
        trading_settings.save()

        print("[{}] Trading settings initialized successful.".format(utils.get_now()))
    else:
        print("[{}] Trading settings already initialized!".format(utils.get_now()))

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
