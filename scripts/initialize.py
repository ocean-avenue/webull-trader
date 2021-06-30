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
            algo_type=enums.AlgorithmType.DAY_MOMENTUM,
            order_amount_limit=1000.0,
            extended_order_amount_limit=1000.0,
            min_surge_amount=15000.0,
            min_surge_volume=6000,
            min_surge_change_ratio=0.04,
            avg_confirm_volume=300000,
            extended_avg_confirm_volume=3000,
            avg_confirm_amount=3000000,
            extended_avg_confirm_amount=30000,
            observe_timeout_in_sec=300,
            trade_interval_in_sec=120,
            pending_order_timeout_in_sec=60,
            holding_order_timeout_in_sec=1800,
            max_bid_ask_gap_ratio=0.02,
            target_profit_ratio=0.02,
            stop_loss_ratio=-0.01,
            refresh_login_interval_in_min=10,
            blacklist_timeout_in_sec=1800,
            swing_position_amount_limit=1000.0,
            max_prev_day_close_gap_ratio=0.02,
            min_relative_volume=3.0,
            min_earning_gap_ratio=0.05,
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
