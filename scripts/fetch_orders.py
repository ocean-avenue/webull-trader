# -*- coding: utf-8 -*-

# fetch orders from webull account into database

def start():
    from sdk import webullsdk
    from scripts import utils

    paper = utils.check_paper()
    webullsdk.login(paper=paper)

    # fetch enough count to cover today's orders
    history_orders = webullsdk.get_history_orders(
        status='All', count=1000)[::-1]

    for order_data in history_orders:
        print(order_data)
        utils.save_webull_order(order_data, paper=paper)


if __name__ == "django.core.management.commands.shell":
    start()
