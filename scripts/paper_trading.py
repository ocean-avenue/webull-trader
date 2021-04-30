# -*- coding: utf-8 -*-

MIN_SURGE_AMOUNT = 21000
MIN_SURGE_VOL = 1000
SURGE_MIN_CHANGE_PERCENTAGE = 4  # at least 8% change for surge
TRADE_TIMEOUT = 5  # trading timeout in minutes
PENDING_ORDER_TIMEOUT = 60  # pending order timeout in seconds
HOLDING_ORDER_TIMEOUT = 1800  # holding order timeout in seconds
REFRESH_LOGIN_INTERVAL = 10  # refresh login interval minutes
BUY_AMOUNT = 1000
MAX_GAP = 0.02
PROFIT_RATE = 0.02
LOSS_RATE = -0.01


def start():
    import time
    from datetime import datetime, timedelta
    from sdk import webullsdk
    from scripts import utils

    global MIN_SURGE_AMOUNT
    global MIN_SURGE_VOL
    global SURGE_MIN_CHANGE_PERCENTAGE
    global TRADE_TIMEOUT
    global PENDING_ORDER_TIMEOUT
    global HOLDING_ORDER_TIMEOUT
    global REFRESH_LOGIN_INTERVAL
    global BUY_AMOUNT
    global MAX_GAP
    global PROFIT_RATE
    global LOSS_RATE

    while not utils.is_market_hour():
        print("[{}] Waiting for market hour...".format(utils.get_now()))
        time.sleep(10)

    print("[{}] Trading started...".format(utils.get_now()))

    webullsdk.login(paper=True)
    print("[{}] Webull logged in".format(utils.get_now()))
    last_login_refresh_time = datetime.now()

    tracking_tickers = {}

    def _check_buy_order_filled(ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] Checking buy order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
        order_filled = False
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = True
                quantity = int(position['position'])
                cost = float(position['costPrice'])
                # update tracking_tickers
                tracking_tickers[symbol]['positions'] = quantity
                tracking_tickers[symbol]['pending_buy'] = False
                tracking_tickers[symbol]['pending_order_id'] = None
                tracking_tickers[symbol]['pending_order_time'] = None
                tracking_tickers[symbol]['order_filled_time'] = datetime.now()
                print("[{}] Buy order <{}>[{}] filled, cost: {}".format(
                    utils.get_now(), symbol, ticker_id, cost))
                break
        if not order_filled:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=PENDING_ORDER_TIMEOUT):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(
                        ticker['pending_order_id'], "Buy order timeout, canceled!")
                    print("[{}] Buy order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                    tracking_tickers[symbol]['pending_buy'] = False
                    tracking_tickers[symbol]['pending_order_id'] = None
                    tracking_tickers[symbol]['pending_order_time'] = None
                else:
                    print("[{}] Failed to cancel timeout buy order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def _check_sell_order_filled(ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] Checking sell order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
        order_filled = True
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = False
        if order_filled:
            # check if have any exit note
            exit_note = tracking_tickers[symbol]['exit_note']
            if exit_note:
                utils.save_webull_order_note(
                    tracking_tickers[symbol]['pending_order_id'], exit_note)
            # update tracking_tickers
            tracking_tickers[symbol]['positions'] = 0
            tracking_tickers[symbol]['pending_sell'] = False
            tracking_tickers[symbol]['pending_order_id'] = None
            tracking_tickers[symbol]['pending_order_time'] = None
            tracking_tickers[symbol]['exit_note'] = None
            print("[{}] Sell order <{}>[{}] filled".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del tracking_tickers[symbol]
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=PENDING_ORDER_TIMEOUT):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(
                        ticker['pending_order_id'], "Sell order timeout, canceled!")
                    print("[{}] Sell order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                    # resubmit sell order
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    if quote == None:
                        return
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    holding_quantity = ticker['positions']
                    order_response = webullsdk.sell_limit_order(
                        ticker_id=ticker_id,
                        price=bid_price,
                        quant=holding_quantity)
                    print("[{}] Resubmit sell order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        utils.save_webull_order_note(
                            order_response['orderId'], "Resubmit sell order.")
                        # mark pending sell
                        tracking_tickers[symbol]['pending_sell'] = True
                        tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                else:
                    print("[{}] Failed to cancel timeout sell order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def _do_trade(ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        pending_buy = ticker['pending_buy']
        if pending_buy:
            _check_buy_order_filled(ticker)
            return

        pending_sell = ticker['pending_sell']
        if pending_sell:
            _check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last TRADE_TIMEOUT minutes
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(minutes=TRADE_TIMEOUT):
            print("[{}] Trading <{}>[{}] session timeout!".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del tracking_tickers[symbol]
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            bars = utils.convert_2m_bars(
                webullsdk.get_1m_bars(ticker_id, count=60))
            if bars.empty:
                return

            if not utils.check_bars_updated(bars):
                print("[{}] <{}>[{}] charts is not updated, stop trading!".format(
                    utils.get_now(), symbol, ticker_id))
                # remove from monitor
                del tracking_tickers[symbol]
                return

            # if utils.check_bars_price_fixed(bars):
            #     print("[{}] <{}>[{}] Price is fixed during last 3 candles...".format(
            #         utils.get_now(), symbol, ticker_id))
            #     # remove from monitor
            #     del tracking_tickers[symbol]
            #     return

            # calculate and fill ema 9 data
            bars['ema9'] = bars['close'].ewm(span=9, adjust=False).mean()
            current_candle = bars.iloc[-1]
            prev_candle = bars.iloc[-2]

            # current price data
            current_low = current_candle['low']
            current_vwap = current_candle['vwap']
            current_ema9 = current_candle['ema9']
            current_volume = int(current_candle['volume'])
            # check low price above vwap and ema 9
            if current_low > current_vwap and current_low > current_ema9:
                # check first candle make new high
                if current_candle['high'] > prev_candle['high']:
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    if quote == None:
                        return
                    ask_price = float(
                        quote['depth']['ntvAggAskList'][0]['price'])
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    gap = (ask_price - bid_price) / bid_price
                    if gap > MAX_GAP:
                        print("[{}] <{}>[{}] gap too large, ask: {}, bid: {}, stop trading!".format(
                            utils.get_now(), symbol, ticker_id, ask_price, bid_price))
                        # remove from monitor
                        del tracking_tickers[symbol]
                        return
                    buy_quant = (int)(BUY_AMOUNT / ask_price)
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    print("[{}] Trading <{}>[{}], low: {}, vwap: {}, ema9: {}, volume: {}".format(
                        utils.get_now(), symbol, ticker_id, current_low, current_vwap, round(current_ema9, 3), current_volume))
                    print("[{}] 🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, buy_quant, ask_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        # mark pending buy
                        tracking_tickers[symbol]['pending_buy'] = True
                        tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
        else:
            positions = webullsdk.get_positions()
            if positions == None:
                return
            ticker_position = None
            for position in positions:
                if position['ticker']['symbol'] == symbol:
                    ticker_position = position
                    break
            if not ticker_position:
                print("[{}] Finding <{}>[{}] position error!".format(
                    utils.get_now(), symbol, ticker_id))
                return
            # cost = float(ticker_position['cost'])
            # last_price = float(ticker_position['lastPrice'])
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate
            # quantity = int(ticker_position['position'])
            # print("[{}] Checking <{}>[{}], cost: {}, last: {}, change: {}%".format(
            #     utils.get_now(), symbol, ticker_id, cost, last_price, round(profit_loss_rate * 100, 2)))
            exit_trading = False
            # sell if drawdown 1% from max P&L rate
            # if max_profit_loss_rate - profit_loss_rate >= 0.01:
            #     exit_trading = True
            # simply observe profit/loss ratio
            if profit_loss_rate >= PROFIT_RATE or profit_loss_rate <= LOSS_RATE:
                exit_trading = True
            exit_note = None
            # check if holding too long
            if (datetime.now() - ticker['order_filled_time']) >= timedelta(seconds=HOLDING_ORDER_TIMEOUT) and profit_loss_rate < 0.01:
                print("[{}] Holding <{}>[{}] too long!".format(
                    utils.get_now(), symbol, ticker_id))
                exit_note = "Holding too long!"
                exit_trading = True
            # check if price go sideway
            # if quote != None:
            #     if float(quote['pChRatio']) == 0.0:
            #         print("[{}] <{}>[{}] price is going sideway...".format(
            #             utils.get_now(), symbol, ticker_id))
            #         exit_trading = True
            if not exit_trading:
                # fetch 1m bar charts
                bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=20))
                if utils.check_bars_price_fixed(bars):
                    print("[{}] <{}>[{}] Price is fixed during last 3 candles...".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Price is fixed during last 3 candles..."
                    exit_trading = True

            # exit trading
            if exit_trading:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = float(
                    quote['depth']['ntvAggBidList'][0]['price'])
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=holding_quantity)
                print("[{}] 📈 Exit trading <{}>[{}] P&L: {}%".format(
                    utils.get_now(), symbol, ticker_id, round(profit_loss_rate * 100, 2)))
                print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
                if 'msg' in order_response:
                    print("[{}] {}".format(
                        utils.get_now(), order_response['msg']))
                else:
                    # mark pending sell
                    tracking_tickers[symbol]['pending_sell'] = True
                    tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                    tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                    )
                    tracking_tickers[symbol]['exit_note'] = exit_note

        # TODO, buy after the first pull back

    def _do_clear(ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        pending_buy = ticker['pending_buy']
        if pending_buy:
            _check_buy_order_filled(ticker)
            return

        pending_sell = ticker['pending_sell']
        if pending_sell:
            _check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        if holding_quantity == 0:
            # remove from monitor
            del tracking_tickers[symbol]
            return

        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return
        bid_price = float(quote['depth']['ntvAggBidList'][0]['price'])
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=bid_price,
            quant=holding_quantity)
        print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
            utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
        if 'msg' in order_response:
            print("[{}] {}".format(utils.get_now(), order_response['msg']))
        else:
            # mark pending sell
            tracking_tickers[symbol]['pending_sell'] = True
            tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            tracking_tickers[symbol]['pending_order_time'] = datetime.now()

    # main loop
    while utils.is_market_hour():
        # trading tickers
        for symbol in list(tracking_tickers):
            ticker = tracking_tickers[symbol]
            _do_trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if utils.is_regular_market_hour():
            top_gainers = webullsdk.get_top_gainers()
        elif utils.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif utils.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # print("[{}] Scanning top gainers [{}]...".format(
        #     utils.get_now(), ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            # check if ticker already in monitor
            if symbol in tracking_tickers:
                continue
            ticker_id = gainer["ticker_id"]
            # print("[{}] Scanning <{}>[{}]...".format(
            #     utils.get_now(), symbol, ticker_id))
            change_percentage = gainer["change_percentage"]
            # check if change >= 8%
            if change_percentage * 100 >= SURGE_MIN_CHANGE_PERCENTAGE:
                bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=60))
                if bars.empty:
                    continue
                latest_candle = bars.iloc[-1]
                if utils.check_bars_updated(bars):
                    latest_close = latest_candle["close"]
                    latest_vwap = latest_candle["vwap"]
                    volume = int(latest_candle["volume"])
                    # check if trasaction amount meets requirement
                    if latest_close * volume >= MIN_SURGE_AMOUNT and volume >= MIN_SURGE_VOL and latest_close >= latest_vwap:
                        # found trading ticker
                        ticker = {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "pending_buy": False,
                            "pending_sell": False,
                            "pending_order_id": None,
                            "pending_order_time": None,
                            "order_filled_time": None,
                            "positions": 0,
                            "start_time": datetime.now(),
                            # paper trade do not have stop trailing order, this value keep track of max P&L
                            "max_profit_loss_rate": 0,
                            "exit_note": None,
                        }
                        tracking_tickers[symbol] = ticker
                        print("[{}] Found <{}>[{}] to trade!".format(
                            utils.get_now(), symbol, ticker_id))

        # refresh login
        if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=REFRESH_LOGIN_INTERVAL):
            webullsdk.login(paper=True)
            print("[{}] Refresh webull login".format(utils.get_now()))
            last_login_refresh_time = datetime.now()

        # at least slepp 1 sec
        time.sleep(1)

    # check if still holding any positions before exit
    while len(list(tracking_tickers)) > 0:
        for symbol in list(tracking_tickers):
            ticker = tracking_tickers[symbol]
            _do_clear(ticker)

        # at least slepp 1 sec
        time.sleep(1)

    print("[{}] Trading ended!".format(utils.get_now()))

    # output today's proft loss
    portfolio = webullsdk.get_portfolio()
    print("[{}] Today's P&L: {}".format(
        utils.get_now(), portfolio['dayProfitLoss']))

    # webullsdk.logout()
    # print("[{}] Webull logged out".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()
