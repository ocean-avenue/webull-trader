# -*- coding: utf-8 -*-

# fetch orders from webull account into database


FETCH_ORDER_COUNT = 100


def start():
    from datetime import date
    from sdk import webullsdk
    from common import utils
    from webull_trader.models import WebullOrder, WebullOrderNote

    global FETCH_ORDER_COUNT

    paper = utils.check_paper()

    if webullsdk.login(paper=paper):
        # fetch enough count to cover today's orders
        history_orders = webullsdk.get_history_orders(
            status='All', count=FETCH_ORDER_COUNT)[::-1]

        for order_data in history_orders:
            utils.save_webull_order(order_data, paper=paper)

    day = date.today()
    all_day_orders = WebullOrder.objects.filter(filled_time__year=str(
        day.year), filled_time__month=str(day.month), filled_time__day=str(day.day))

    # fill all order with setup
    for order in all_day_orders:
        order_id = order.order_id
        order_note = WebullOrderNote.objects.filter(order_id=order_id).first()
        if order_note:
            order.setup = order_note.setup
            order.save()


if __name__ == "django.core.management.commands.shell":
    start()
