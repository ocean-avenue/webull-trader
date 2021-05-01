# -*- coding: utf-8 -*-

# import orders from webull paper account to database

def start():
    from sdk import webullsdk
    from scripts import utils

    webullsdk.login(paper=True)

    # fetch enough count to cover today's orders
    history_orders = webullsdk.get_history_orders(
        status='All', count=1000)[::-1]

    for order_data in history_orders:
        utils.save_webull_order(order_data, paper=True)


if __name__ == "django.core.management.commands.shell":
    start()
