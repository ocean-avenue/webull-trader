# -*- coding: utf-8 -*-

# migrate to new swing position, trade model with order_ids


def start():

    from webull_trader.models import SwingPosition, SwingTrade, WebullOrder
    from webull_trader.enums import ActionType
    from scripts import utils

    SWING_POSITIONS_ORDER_IDS = [
        {
            "symbol": "TSM",
            "order_ids": "469385076887556096",
        },
        {
            "symbol": "KO",
            "order_ids": "469384825548099584",
        },
        {
            "symbol": "MP",
            "order_ids": "468660075708338176",
        },
        {
            "symbol": "TMUS",
            "order_ids": "466848369441001472",
        },
        {
            "symbol": "PTON",
            "order_ids": "463586786350778368",
        },
        {
            "symbol": "JKS",
            "order_ids": "463586638837092352",
        },
        {
            "symbol": "ARKK",
            "order_ids": "463586362793170944",
        },
    ]

    for swing_order_ids in SWING_POSITIONS_ORDER_IDS:
        swing_position = SwingPosition.objects.filter(
            symbol=swing_order_ids["symbol"]).first()
        N = utils.get_avg_true_range(swing_order_ids["symbol"])
        order_ids = swing_order_ids["order_ids"].split(",")
        total_cost = 0.0
        quantity = 0
        units = 0
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if webull_order.action == ActionType.BUY:
                total_cost += (webull_order.avg_price *
                               webull_order.filled_quantity)
                quantity += webull_order.filled_quantity
                units += 1
            # update buy date, buy time
            if i == 0:
                swing_position.buy_date = webull_order.filled_time.date()
                swing_position.buy_time = webull_order.filled_time
            # update add_unit_price, stop_loss_price
            if i == len(order_ids) - 1:
                # add unit price
                add_unit_price = round(webull_order.avg_price + N, 2)
                swing_position.add_unit_price = add_unit_price
                # stop loss price
                stop_loss_price = round(webull_order.avg_price - 2 * N, 2)
                swing_position.stop_loss_price = stop_loss_price
            # adding a second time is ok, it will not duplicate the relation
            swing_position.orders.add(webull_order)
        # update total cost
        swing_position.total_cost = round(total_cost, 2)
        # update quantity
        swing_position.quantity = quantity
        # update units
        swing_position.units = units
        # reset require_adjustment
        swing_position.require_adjustment = False
        # update order_ids
        swing_position.order_ids = swing_order_ids["order_ids"]
        # save
        swing_position.save()

    print("[{}] Migrate {} swing positions done".format(
        utils.get_now(), len(SWING_POSITIONS_ORDER_IDS)))

    SWING_TRADE_ORDER_IDS = [
        {
            "symbol": "ARKQ",
            "order_ids": "463586375166337024,469746959821873152",
        },
        {
            "symbol": "NIO",
            "order_ids": "463586714699440128,469384893583851520",
        },
        {
            "symbol": "ARKG",
            "order_ids": "463586391188574208,469384583532529664",
        },
        {
            "symbol": "FUTU",
            "order_ids": "463586554074398720,467210400451006464",
        },
        {
            "symbol": "EH",
            "order_ids": "463586521098786816,466847988010979328",
        },
    ]

    for swing_order_ids in SWING_TRADE_ORDER_IDS:
        swing_trade = SwingTrade.objects.filter(
            symbol=swing_order_ids["symbol"]).first()
        order_ids = swing_order_ids["order_ids"].split(",")
        total_cost = 0.0
        total_sold = 0.0
        quantity = 0
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if webull_order.action == ActionType.BUY:
                total_cost += (webull_order.avg_price *
                               webull_order.filled_quantity)
                quantity += webull_order.filled_quantity
            elif webull_order.action == ActionType.SELL:
                total_sold += (webull_order.avg_price *
                               webull_order.filled_quantity)
            # update buy date, buy time
            if i == 0:
                swing_trade.buy_date = webull_order.filled_time.date()
                swing_trade.buy_time = webull_order.filled_time
            # update sell date, sell time
            if i == len(order_ids) - 1:
                swing_trade.sell_date = webull_order.filled_time.date()
                swing_trade.sell_time = webull_order.filled_time
            # adding a second time is ok, it will not duplicate the relation
            swing_trade.orders.add(webull_order)
        # update total cost
        swing_trade.total_cost = round(total_cost, 2)
        # update total sold
        swing_trade.total_sold = round(total_sold, 2)
        # update quantity
        swing_trade.quantity = quantity
        # reset require_adjustment
        swing_trade.require_adjustment = False
        # update order_ids
        swing_trade.order_ids = swing_order_ids["order_ids"]
        # save
        swing_trade.save()

    print("[{}] Migrate {} swing trades done".format(
        utils.get_now(), len(SWING_TRADE_ORDER_IDS)))


if __name__ == "django.core.management.commands.shell":
    start()
