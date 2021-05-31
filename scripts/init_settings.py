# -*- coding: utf-8 -*-

# init trading settings


def start():
    from scripts import utils
    from webull_trader import enums
    from webull_trader.models import TradingSettings

    trading_settings = TradingSettings.objects.first()
    if trading_settings:
        print("[{}] Trading settings already initialized!".format(utils.get_now()))
        return

    trading_settings = TradingSettings(
        paper=True,
        algo_type=enums.AlgorithmType.DAY_MOMENTUM,
        order_amount_limit=1000.0,
        min_surge_amount=15000.0,
        min_surge_volume=3000,
        min_surge_change_ratio=0.04,
        avg_confirm_volume=6000,
        observe_timeout_in_sec=300,
        trade_interval_in_sec=120,
        pending_order_timeout_in_sec=60,
        holding_order_timeout_in_sec=1800,
        max_bid_ask_gap_ratio=0.02,
        target_profit_ratio=0.02,
        stop_loss_ratio=-0.01,
        refresh_login_interval_in_min=10,
        blacklist_timeout_in_sec=1800,
        swing_position_amount_limit=2000.0,
        max_prev_day_close_gap_ratio=0.02,
        min_relative_volume=3.0,
        min_earning_gap_ratio=0.04,
    )
    trading_settings.save()

    print("[{}] Trading settings initialized successful".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()
