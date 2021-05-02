# -*- coding: utf-8 -*-

# fetch orders from webull account into database

def start():
    from sdk import webullsdk
    from scripts import utils
    from old_ross.models import TradingSettings

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print("[{}] Cannot find trading settings, exit!".format(utils.get_now()))
        return

    webullsdk.login(paper=trading_settings.paper)

    # fetch enough count to cover today's orders
    history_orders = webullsdk.get_history_orders(
        status='All', count=1000)[::-1]

    for order_data in history_orders:
        utils.save_webull_order(order_data, paper=trading_settings.paper)


if __name__ == "django.core.management.commands.shell":
    start()
