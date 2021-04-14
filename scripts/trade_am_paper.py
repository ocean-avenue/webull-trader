# -*- coding: utf-8 -*-

PAPER_TRADE = True

MIN_SURGE_AMOUNT = 21000
MIN_SURGE_VOL = 3000
SURGE_MIN_CHANGE_PERCENTAGE = 8  # at least 8% change for surge
TRADE_TIMEOUT = 5  # trading time out in minutes
BUY_AMOUNT = 1000
HOLDING_POSITION = False
MAX_GAP = 0.02


def start():
    import time
    from datetime import datetime, timedelta
    from sdk import webullsdk

    global PAPER_TRADE
    global MIN_SURGE_AMOUNT
    global MIN_SURGE_VOL
    global SURGE_MIN_CHANGE_PERCENTAGE
    global TRADE_TIMEOUT
    global BUY_AMOUNT
    global MAX_GAP

    def _get_now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _is_after_market():
        now = datetime.now()
        if now.hour < 13 or now.hour >= 17:
            return False
        if now.hour == 13 and now.minute == 0 and now.second < 30:
            return False
        return True

    while not _is_after_market():
        print("[{}] wait for after market open...".format(_get_now()))
        time.sleep(1)

    print("[{}] after market trading started!".format(_get_now()))

    print("[{}] login webull...".format(_get_now()))
    webullsdk.login(paper=PAPER_TRADE)

    trading_ticker = None

    # https://school.stockcharts.com/doku.php?id=technical_indicators:moving_averages
    def _calculate_ema9(charts):
        multiplier = 2 / (9 + 1)
        charts_length = len(charts)
        for i in range(0, charts_length):
            candle = charts[charts_length - i - 1]
            if i < 8:
                candle['ema9'] = 0
            elif i == 8:
                # use sma for initial ema
                sum = 0.0
                for j in (0, 8):
                    c = charts[charts_length - j - 1]
                    sum += c['close']
                candle['ema9'] = round(sum / 9, 2)
            else:
                prev_candle = charts[charts_length - i]
                candle['ema9'] = round(
                    (candle['close'] - prev_candle['ema9']) * multiplier + prev_candle['ema9'], 2)
        return charts

    def _trade(charts):

        global HOLDING_POSITION

        symbol = trading_ticker['symbol']
        ticker_id = trading_ticker['ticker_id']

        # check timeout, skip this ticker if no trade during last 6 minutes
        now_time = datetime.now()
        if not HOLDING_POSITION and (now_time - trading_ticker['start_time']) >= timedelta(minutes=TRADE_TIMEOUT):
            print("[{}] trading <{}>[{}] timeout!".format(
                _get_now(), symbol, ticker_id))
            return True
        # calculate and fill ema 9 data
        _calculate_ema9(charts)
        current_candle = charts[0]
        prev_candle = charts[1]
        if not HOLDING_POSITION:
            current_low = current_candle['low']
            current_vwap = current_candle['vwap']
            current_ema9 = current_candle['ema9']
            current_volume = current_candle['volume']
            print("[{}] trading <{}>[{}], low: {}, vwap: {}, ema9: {}, volume: {}".format(
                _get_now(), symbol, ticker_id, current_low, current_vwap, current_ema9, current_volume))
            # check low price above vwap and ema 9
            if current_low > current_candle['vwap'] and current_low > current_candle['ema9']:
                # check first candle make new high
                if current_candle['high'] > prev_candle['high']:
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    ask_price = float(
                        quote['depth']['ntvAggAskList'][0]['price'])
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    gap = (ask_price - bid_price) / bid_price
                    if gap > MAX_GAP:
                        print("[{}] stop <{}>[{}], ask: {}, bid: {}, gap too large!".format(
                            _get_now(), symbol, ticker_id, ask_price, bid_price))
                        return True
                    buy_quant = (int)(BUY_AMOUNT / ask_price)
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    print("[{}] submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                        _get_now(), symbol, ticker_id, buy_quant, ask_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            _get_now(), order_response['msg']))
                    else:
                        # wait until order filled
                        order_filled = False
                        while not order_filled:
                            print(
                                "[{}] checking order <{}>[{}] filled...".format(_get_now(), symbol, ticker_id))
                            positions = webullsdk.get_positions()
                            if len(positions) > 0:
                                order_filled = True
                                HOLDING_POSITION = True
                                print(
                                    "[{}] order <{}>[{}] has been filled!".format(_get_now(), symbol, ticker_id))
                            if order_filled:
                                break
                            # wait 1 sec
                            time.sleep(1)
        else:
            positions = webullsdk.get_positions()
            if len(positions) == 0:
                print("[{}] error <{}>[{}], no position".format(
                    _get_now(), symbol, ticker_id))
            position = positions[0]
            cost = float(position['cost'])
            last_price = float(position['lastPrice'])
            profit_loss_rate = float(position['unrealizedProfitLossRate'])
            quantity = int(position['position'])
            print("[{}] checking <{}>[{}], cost: {}, last: {}, change: {}%".format(
                _get_now(), symbol, ticker_id, cost, last_price, round(profit_loss_rate * 100, 2)))
            # simple count profit 2% and stop loss 1%
            if profit_loss_rate >= 0.02 or profit_loss_rate < -0.01:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                bid_price = float(
                    quote['depth']['ntvAggBidList'][0]['price'])
                order_response = order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=quantity)
                print("[{}] submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    _get_now(), symbol, ticker_id, quantity, bid_price))
                # wait until order filled
                order_filled = False
                while not order_filled:
                    # TODO, re-submit sell order if timeout
                    print("[{}] checking order <{}>[{}] filled...".format(
                        _get_now(), symbol, ticker_id))
                    positions = webullsdk.get_positions()
                    if len(positions) == 0:
                        order_filled = True
                        HOLDING_POSITION = False
                        print("[{}] order <{}>[{}] has been filled!".format(
                            _get_now(), symbol, ticker_id))
                    if order_filled:
                        break
                    # wait 1 sec
                    time.sleep(1)

                if order_filled:
                    return True

        # TODO, buy after the first pull back
        # TODO, take profit along the way (sell half, half, half...)

        return False

    # main loop
    while _is_after_market():
        if trading_ticker:
            # already found trading ticker
            ticker_id = trading_ticker["ticker_id"]
            charts = webullsdk.get_1m_charts(ticker_id)
            if _trade(charts):
                trading_ticker = None
        else:
            # find trading ticker in top gainers
            top_gainers = webullsdk.get_after_market_gainers()
            top_10_gainers = top_gainers[:10]

            for gainer in top_10_gainers:
                symbol = gainer["symbol"]
                ticker_id = gainer["ticker_id"]
                print("[{}] scanning <{}>[{}]...".format(
                    _get_now(), symbol, ticker_id))
                change_percentage = gainer["change_percentage"]
                # check if change >= 8%
                if change_percentage * 100 >= SURGE_MIN_CHANGE_PERCENTAGE:
                    charts = webullsdk.get_1m_charts(ticker_id)
                    latest_chart = charts[0]
                    latest_timestamp = latest_chart["timestamp"]
                    current_timestamp = int(datetime.timestamp(datetime.now()))
                    # check if have valid latest chart data, delay no more than 1 minute
                    if current_timestamp - latest_timestamp <= 60:
                        latest_close = latest_chart["close"]
                        volume = latest_chart["volume"]
                        # check if trasaction amount meets requirement
                        if (
                            latest_close * volume >= MIN_SURGE_AMOUNT
                            and volume >= MIN_SURGE_VOL
                        ):
                            # found trading ticker
                            trading_ticker = {
                                "symbol": symbol,
                                "ticker_id": ticker_id,
                                "start_time": datetime.now(),
                            }
                            print("[{}] found <{}>[{}] to trade!".format(
                                _get_now(), symbol, ticker_id))
                            if _trade(charts):
                                trading_ticker = None
                            break

        time.sleep(5)

    print("[{}] logout webull...".format(_get_now()))
    webullsdk.logout()

    print("[{}] after market trading ended!".format(_get_now()))


if __name__ == "django.core.management.commands.shell":
    start()