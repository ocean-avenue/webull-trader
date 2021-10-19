# -*- coding: utf-8 -*-

# migrate day trade adjustment, trade model with order_ids


def start():
    from webull_trader.models import DayTrade
    from common import utils

    buy_orders, sell_orders = utils.get_day_trade_orders()
    day_trades = utils.get_trades_from_orders(buy_orders, sell_orders)

    for day_trade in day_trades:
        if 'sell_order_id' not in day_trade:
            print("[{}] Day trade sell_order_id not existed, skip...".format(
                utils.get_now()))
            continue
        order_ids = "{},{}".format(
            day_trade['buy_order_id'], day_trade['sell_order_id'])
        trade = DayTrade.objects.filter(order_ids=order_ids).first()
        buy_order = day_trade['buy_order']
        sell_order = day_trade['sell_order']
        if trade:
            print("[{}] Day trade {} already existed, skip...".format(
                utils.get_now(), order_ids))
            trade.orders.add(buy_order)
            trade.orders.add(sell_order)
            continue
        trade = DayTrade(
            symbol=day_trade['symbol'],
            ticker_id=day_trade['ticker_id'],
            order_ids=order_ids,
            total_cost=round(day_trade['buy_price']
                             * day_trade['quantity'], 2),
            total_sold=round(day_trade['sell_price']
                             * day_trade['quantity'], 2),
            quantity=day_trade['quantity'],
            buy_date=day_trade['buy_time'].date(),
            buy_time=day_trade['buy_time'],
            sell_date=day_trade['sell_time'].date(),
            sell_time=day_trade['sell_time'],
            setup=day_trade['setup'],
            require_adjustment=False,
        )
        trade.save()
        trade.orders.add(buy_order)
        trade.orders.add(sell_order)
        print("[{}] Day trade {} created!".format(
            utils.get_now(), order_ids))


if __name__ == "django.core.management.commands.shell":
    start()
