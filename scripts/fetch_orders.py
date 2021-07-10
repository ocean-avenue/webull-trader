# -*- coding: utf-8 -*-

# fetch orders from webull account into database
FETCH_ORDER_COUNT = 100


def start():
    from sdk import webullsdk
    from scripts import utils

    global FETCH_ORDER_COUNT

    paper = utils.check_paper()

    if webullsdk.login(paper=paper):
        # fetch enough count to cover today's orders
        history_orders = webullsdk.get_history_orders(
            status='All', count=FETCH_ORDER_COUNT)[::-1]

        for order_data in history_orders:
            utils.save_webull_order(order_data, paper=paper)


if __name__ == "django.core.management.commands.shell":
    start()
