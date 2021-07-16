# -*- coding: utf-8 -*-

# fill webull order with setup from order note


def start():
    from webull_trader.models import WebullOrder, WebullOrderNote, SwingPosition, SwingTrade
    from scripts import utils

    all_orders = WebullOrder.objects.all()

    # fill all order with setup
    for order in all_orders:
        order_id = order.order_id
        order_note = WebullOrderNote.objects.filter(order_id=order_id).first()
        if order_note:
            order.setup = order_note.setup
            order.save()
        # else:
        #     print("[{}] Cannot find order {}'s note object!".format(
        #         utils.get_now(), order_id))

    # fill all swing positions's order
    all_positions = SwingPosition.objects.all()
    for position in all_positions:
        order_ids = position.order_ids.split(',')
        for order_id in order_ids:
            order = WebullOrder.objects.filter(order_id=order_id).first()
            if order:
                order.setup = position.setup
                order.save()

    # fill all swing trades's order
    all_trades = SwingTrade.objects.all()
    for trade in all_trades:
        order_ids = trade.order_ids.split(',')
        for order_id in order_ids:
            order = WebullOrder.objects.filter(order_id=order_id).first()
            if order:
                order.setup = trade.setup
                order.save()

    print("[{}] Migrate {} webull orders setup done".format(
        utils.get_now(), len(all_orders)))


if __name__ == "django.core.management.commands.shell":
    start()
