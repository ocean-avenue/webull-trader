# -*- coding: utf-8 -*-

# fetch orders from webull account into database


FETCH_ORDER_COUNT = 100


def start():
    from datetime import date
    from sdk import webullsdk
    from common import utils
    from webull_trader.models import WebullOrder

    global FETCH_ORDER_COUNT

    paper = utils.check_paper()

    if webullsdk.login(paper=paper):
        # fetch enough count to cover today's orders
        history_orders = webullsdk.get_history_orders(
            status=webullsdk.ORDER_STATUS_ALL, count=FETCH_ORDER_COUNT)[::-1]

        for order_data in history_orders:
            utils.save_webull_order(order_data, paper=paper)

    day = date.today()
    all_day_orders = WebullOrder.objects.filter(filled_time__year=str(
        day.year), filled_time__month=str(day.month), filled_time__day=str(day.day))


if __name__ == "django.core.management.commands.shell":
    start()
