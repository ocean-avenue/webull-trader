import pytz
from django.conf import settings
from datetime import datetime
from common import enums, utils
from webull_trader.models import WebullOrder


def _order_action_fmt(action_str):
    action = enums.ActionType.BUY
    if action_str == "SELL":
        action = enums.ActionType.SELL
    return action


def _order_type_fmt(type_str):
    order_type = enums.OrderType.LMT
    if type_str == "MKT":
        order_type = enums.OrderType.MKT
    elif type_str == "STP":
        order_type = enums.OrderType.STP
    elif type_str == "STP LMT":
        order_type = enums.OrderType.STP_LMT
    elif type_str == "STP TRAIL":
        order_type = enums.OrderType.STP_TRAIL
    return order_type


def _order_time_fmt(order_time_str):
    time_fmt = "%m/%d/%Y %H:%M:%S EDT"
    if "EST" in order_time_str:
        time_fmt = "%m/%d/%Y %H:%M:%S EST"
    return pytz.timezone(settings.TIME_ZONE).localize(datetime.strptime(order_time_str, time_fmt))


def _time_in_force_fmt(time_in_force_str):
    time_in_force = enums.TimeInForceType.GTC
    if time_in_force_str == "DAY":
        time_in_force = enums.TimeInForceType.DAY
    elif time_in_force_str == "IOC":
        time_in_force = enums.TimeInForceType.IOC
    return time_in_force


def save_webull_order(order_data, paper=True):
    avg_price = 0.0
    price = 0.0
    filled_time = None
    placed_time = None
    create_time = None
    if paper:
        order_id = str(order_data['orderId'])
        if "symbol" in order_data['ticker']:
            symbol = order_data['ticker']['symbol']
        else:
            symbol = order_data['ticker']['disSymbol']
        ticker_id = str(order_data['ticker']['tickerId'])
        action = _order_action_fmt(order_data['action'])
        status = order_data['statusStr']
        order_type = _order_type_fmt(order_data['orderType'])
        total_quantity = int(order_data['totalQuantity'])
        filled_quantity = int(order_data['filledQuantity'])
        if 'avgFilledPrice' in order_data:
            avg_price = float(order_data['avgFilledPrice'])
            price = avg_price
        if 'lmtPrice' in order_data:
            price = float(order_data['lmtPrice'])
        if 'filledTime' in order_data:
            filled_time = _order_time_fmt(order_data['filledTime'])
        if 'placedTime' in order_data:
            placed_time = _order_time_fmt(order_data['placedTime'])
            create_time = order_data['placedTime']
        time_in_force = _time_in_force_fmt(order_data['timeInForce'])
    else:
        order_obj = order_data['orders'][0]
        order_id = str(order_obj['orderId'])
        if "symbol" in order_obj['ticker']:
            symbol = order_obj['ticker']['symbol']
        else:
            symbol = order_obj['ticker']['disSymbol']
        ticker_id = str(order_obj['ticker']['tickerId'])
        action = _order_action_fmt(order_obj['action'])
        status = order_obj['statusStr']
        order_type = _order_type_fmt(order_obj['orderType'])
        total_quantity = int(order_obj['totalQuantity'])
        filled_quantity = int(order_obj['filledQuantity'])
        if 'avgFilledPrice' in order_obj:
            avg_price = float(order_obj['avgFilledPrice'])
            price = avg_price
        if 'lmtPrice' in order_obj:
            price = float(order_obj['lmtPrice'])
        if 'auxPrice' in order_obj:  # for stop order
            price = float(order_obj['auxPrice'])
        if 'filledTime' in order_obj:
            filled_time = _order_time_fmt(order_obj['filledTime'])
        if 'createTime' in order_obj:
            placed_time = _order_time_fmt(order_obj['createTime'])
            create_time = order_obj['createTime']
        time_in_force = _time_in_force_fmt(order_obj['timeInForce'])

    order = WebullOrder.objects.filter(order_id=order_id).first()
    if order:
        print("[{}] Updating order <{}> {} ({})...".format(
            utils.get_now(), symbol, order_id, create_time))
    else:
        print("[{}] Importing order <{}> {} ({})...".format(
            utils.get_now(), symbol, order_id, create_time))
    if order:
        order.ticker_id = ticker_id
        order.symbol = symbol
        order.action = action
        order.status = status
        order.total_quantity = total_quantity
        order.filled_quantity = filled_quantity
        order.price = price
        order.avg_price = avg_price
        order.order_type = order_type
        order.filled_time = filled_time
        order.placed_time = placed_time
        order.time_in_force = time_in_force
        order.paper = paper
    else:
        order = WebullOrder(
            order_id=order_id,
            ticker_id=ticker_id,
            symbol=symbol,
            action=action,
            status=status,
            total_quantity=total_quantity,
            filled_quantity=filled_quantity,
            price=price,
            avg_price=avg_price,
            order_type=order_type,
            filled_time=filled_time,
            placed_time=placed_time,
            time_in_force=time_in_force,
            paper=paper,
        )
    order.save()
