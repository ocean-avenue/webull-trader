# -*- coding: utf-8 -*-

# adjust trade data by webull order


def start():
    from common import utils
    from common.enums import ActionType
    from webull_trader.models import WebullOrder, SwingPosition, SwingTrade, DayPosition, DayTrade

    # adjust swing position data by filled order
    swing_positions = SwingPosition.objects.filter(require_adjustment=True)
    for swing_position in swing_positions:
        symbol = swing_position.symbol
        N = utils.get_swing_avg_true_range(symbol)
        order_ids = swing_position.order_ids.split(',')
        total_cost = 0.0
        quantity = 0
        units = 0
        uncompleted_order = False
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if not webull_order or webull_order.status != "Filled":
                uncompleted_order = True
                break
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
        # skip if miss order
        if uncompleted_order:
            continue
        # update total cost
        swing_position.total_cost = round(total_cost, 2)
        # update quantity
        swing_position.quantity = quantity
        # update units
        swing_position.units = units
        # reset require_adjustment
        swing_position.require_adjustment = False
        # save
        swing_position.save()

    # adjust swing trade data by filled order
    swing_trades = SwingTrade.objects.filter(require_adjustment=True)
    for swing_trade in swing_trades:
        order_ids = swing_trade.order_ids.split(',')
        total_cost = 0.0
        total_sold = 0.0
        quantity = 0
        setup = swing_trade.setup
        uncompleted_order = False
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if not webull_order or webull_order.status != "Filled":
                uncompleted_order = True
                break
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
            # fill webull order setup
            webull_order.setup = setup
            webull_order.save()
        # skip if miss order
        if uncompleted_order:
            continue
        # update total cost
        swing_trade.total_cost = round(total_cost, 2)
        # update total sold
        swing_trade.total_sold = round(total_sold, 2)
        # update quantity
        swing_trade.quantity = quantity
        # reset require_adjustment
        swing_trade.require_adjustment = False
        # save
        swing_trade.save()

    # adjust day position data by filled order
    day_positions = DayPosition.objects.filter(require_adjustment=True)
    for day_position in day_positions:
        order_ids = day_position.order_ids.split(',')
        total_cost = 0.0
        quantity = 0
        uncompleted_order = False
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if not webull_order or webull_order.status != "Filled":
                uncompleted_order = True
                break
            if webull_order.action == ActionType.BUY:
                total_cost += (webull_order.avg_price *
                               webull_order.filled_quantity)
                quantity += webull_order.filled_quantity
            # update buy date, buy time
            if i == 0:
                day_position.buy_date = webull_order.filled_time.date()
                day_position.buy_time = webull_order.filled_time
            # adding a second time is ok, it will not duplicate the relation
            day_position.orders.add(webull_order)
        # skip if miss order
        if uncompleted_order:
            continue
        # update total cost
        day_position.total_cost = round(total_cost, 2)
        # update quantity
        day_position.quantity = quantity
        # reset require_adjustment
        day_position.require_adjustment = False
        # save
        day_position.save()

    # adjust day trade data by filled order
    day_trades = DayTrade.objects.filter(require_adjustment=True)
    for day_trade in day_trades:
        order_ids = day_trade.order_ids.split(',')
        total_cost = 0.0
        total_sold = 0.0
        buy_quantity = 0
        sell_quantity = 0
        setup = day_trade.setup
        uncompleted_order = False
        for i in range(0, len(order_ids)):
            order_id = order_ids[i]
            webull_order = WebullOrder.objects.filter(
                order_id=order_id).first()
            if not webull_order or webull_order.status != "Filled":
                uncompleted_order = True
                continue
            if webull_order.action == ActionType.BUY:
                total_cost += (webull_order.avg_price *
                               webull_order.filled_quantity)
                buy_quantity += webull_order.filled_quantity
            elif webull_order.action == ActionType.SELL:
                total_sold += (webull_order.avg_price *
                               webull_order.filled_quantity)
                sell_quantity += webull_order.filled_quantity
            # update buy date, buy time
            if i == 0:
                day_trade.buy_date = webull_order.filled_time.date()
                day_trade.buy_time = webull_order.filled_time
            # update sell date, sell time
            if i == len(order_ids) - 1:
                day_trade.sell_date = webull_order.filled_time.date()
                day_trade.sell_time = webull_order.filled_time
            # adding a second time is ok, it will not duplicate the relation
            day_trade.orders.add(webull_order)
            # fill webull order setup
            webull_order.setup = setup
            webull_order.save()
        # update total cost
        day_trade.total_cost = round(total_cost, 2)
        if buy_quantity > sell_quantity:
            total_sold = (total_sold / sell_quantity) * buy_quantity
        # update total sold
        day_trade.total_sold = round(total_sold, 2)
        # update quantity
        day_trade.quantity = buy_quantity
        # may need adjust again later
        if not uncompleted_order:
            # reset require_adjustment
            day_trade.require_adjustment = False
        # save
        day_trade.save()


if __name__ == "django.core.management.commands.shell":
    start()
