# -*- coding: utf-8 -*-

# clear all existing positions


def start():
    from django.utils import timezone
    from sdk import webullsdk
    from common import utils, db
    from webull_trader.models import DayPosition
    from logger import exception_logger

    paper = utils.is_paper_trading()

    algo_type = utils.get_algo_type()
    if utils.is_swing_trade_algo(algo_type):
        return
    if not utils.get_trading_hour():
        return
    if webullsdk.login(paper=paper):
        clear_positions = {}
        while True:
            # cancel all existing order
            webullsdk.cancel_all_orders()
            positions = webullsdk.get_positions()
            if len(positions) == 0:
                break
            for position in positions:
                symbol = position['ticker']['symbol']
                ticker_id = position['ticker']['tickerId']
                holding_quantity = int(position['position'])
                last_price = float(position['lastPrice'])

                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=last_price,
                    quant=holding_quantity)
                order_id = utils.get_order_id_from_response(
                    order_response, paper=paper)
                clear_positions[symbol] = {
                    'ticker_id': ticker_id,
                    'order_id': order_id,
                    'sell_price': last_price,
                }
                exception_logger.log("TradingPositionException", "",
                                     f"⚠️  Exit trading exception position <{symbol}>!")
        for symbol, sell_order in clear_positions:
            order_id = sell_order['order_id']
            ticker_id = sell_order['ticker_id']
            sell_price = sell_order['sell_price']
            position_obj = DayPosition.objects.filter(symbol=symbol).first()
            if not position_obj:
                continue
            # add trade object
            db.add_day_trade(
                symbol=symbol,
                ticker_id=ticker_id,
                position=position_obj,
                order_id=order_id,
                sell_price=sell_price,
                sell_time=timezone.now())
            # remove position object
            position_obj.delete()


if __name__ == "django.core.management.commands.shell":
    start()
