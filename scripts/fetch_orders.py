# -*- coding: utf-8 -*-

# fetch orders from webull account into database


FETCH_ORDER_COUNT = 100


def start():
    from sdk import webullsdk
    from common import utils, db
    from logger import exception_logger

    global FETCH_ORDER_COUNT

    paper = utils.is_paper_trading()

    if webullsdk.login(paper=paper):
        try:
            # fetch enough count to cover today's orders
            history_orders = webullsdk.get_history_orders(
                status=webullsdk.ORDER_STATUS_ALL, count=FETCH_ORDER_COUNT)[::-1]
            for order_data in history_orders:
                db.save_webull_order(order_data, paper=paper)
        except Exception as e:
            exception_logger.log(str(e), f"orders: {str(history_orders)}")


if __name__ == "django.core.management.commands.shell":
    start()
