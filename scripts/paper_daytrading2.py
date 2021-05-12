# -*- coding: utf-8 -*-

# Paper Trading
# Dynamic Optimize - Trade based on win rate, reduce size if win rate is low.


def start():
    import time
    from datetime import datetime, timedelta
    from old_ross.enums import SetupType
    from old_ross.models import TradingSettings
    from sdk import webullsdk
    from scripts import utils

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print("[{}] Cannot find trading settings, quit!".format(utils.get_now()))
        return

    while not utils.is_market_hour():
        print("[{}] Waiting for market hour...".format(utils.get_now()))
        time.sleep(10)

    print("[{}] Trading started...".format(utils.get_now()))
    print("[{}] Algorithm type: Dynamic Optimize - Trade based on win rate, reduce size if win rate is low.".format(utils.get_now()))
    # load settings
    MIN_SURGE_AMOUNT = trading_settings.min_surge_amount
    print("[{}] Min surge amount: {}".format(
        utils.get_now(), MIN_SURGE_AMOUNT))
    MIN_SURGE_VOL = trading_settings.min_surge_volume
    print("[{}] Min surge volume: {}".format(
        utils.get_now(), MIN_SURGE_VOL))
    # at least 8% change for surge
    MIN_SURGE_CHANGE_PERCENTAGE = trading_settings.min_surge_change_ratio
    print("[{}] Min gap change: {}%".format(
        utils.get_now(), round(MIN_SURGE_CHANGE_PERCENTAGE * 100, 2)))
    BUY_ORDER_LIMIT = trading_settings.order_amount_limit
    print("[{}] Buy order limit: {}".format(
        utils.get_now(), BUY_ORDER_LIMIT))
    # observe timeout in seconds
    OBSERVE_TIMEOUT = trading_settings.observe_timeout_in_sec
    print("[{}] Observe timeout: {} sec".format(
        utils.get_now(), OBSERVE_TIMEOUT))
    # buy after sell interval in seconds
    TRADE_INTERVAL = trading_settings.trade_interval_in_sec
    print("[{}] Trade interval: {} sec".format(
        utils.get_now(), TRADE_INTERVAL))
    # pending order timeout in seconds
    PENDING_ORDER_TIMEOUT = trading_settings.pending_order_timeout_in_sec
    print("[{}] Pending order timeout: {} sec".format(
        utils.get_now(), PENDING_ORDER_TIMEOUT))
    # holding order timeout in seconds
    HOLDING_ORDER_TIMEOUT = trading_settings.holding_order_timeout_in_sec
    print("[{}] Holding order timeout: {} sec".format(
        utils.get_now(), HOLDING_ORDER_TIMEOUT))
    # refresh login interval minutes
    REFRESH_LOGIN_INTERVAL = trading_settings.refresh_login_interval_in_min
    print("[{}] Refresh login timeout: {} min".format(
        utils.get_now(), REFRESH_LOGIN_INTERVAL))
    MAX_BID_ASK_GAP = trading_settings.max_bid_ask_gap_ratio
    print("[{}] Max bid ask gap: {}%".format(
        utils.get_now(), round(MAX_BID_ASK_GAP * 100, 2)))
    TARGET_PROFIT_RATE = trading_settings.target_profit_ratio
    print("[{}] Target profit rate: {}%".format(
        utils.get_now(), round(TARGET_PROFIT_RATE * 100, 2)))
    STOP_LOSS_RATE = trading_settings.stop_loss_ratio
    print("[{}] Stop loss rate: {}%".format(
        utils.get_now(), round(STOP_LOSS_RATE * 100, 2)))
    BLACKLIST_TIMEOUT = trading_settings.blacklist_timeout_in_sec
    print("[{}] Blacklist timeout: {} sec".format(
        utils.get_now(), BLACKLIST_TIMEOUT))

    webullsdk.login(paper=True)
    print("[{}] Webull logged in".format(utils.get_now()))
    last_login_refresh_time = datetime.now()

    tracking_tickers = {}
    trading_stats = {}

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
                # TODO save other setup
                utils.save_webull_order_note(
                    ticker['pending_order_id'], setup=SetupType.DAY_FIRST_CANDLE_NEW_HIGH, note="Entry point.")
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
                        ticker['pending_order_id'], note="Buy order timeout, canceled!")
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
                    tracking_tickers[symbol]['pending_order_id'], note=exit_note)
            # update tracking_tickers
            tracking_tickers[symbol]['positions'] = 0
            tracking_tickers[symbol]['pending_sell'] = False
            tracking_tickers[symbol]['pending_order_id'] = None
            tracking_tickers[symbol]['pending_order_time'] = None
            tracking_tickers[symbol]['last_sell_time'] = datetime.now()
            tracking_tickers[symbol]['exit_note'] = None
            # last_profit_loss_rate = tracking_tickers[symbol]['last_profit_loss_rate']
            # # keep in track if > 10% profit, prevent buy back too quick
            # if last_profit_loss_rate != None and last_profit_loss_rate < 0.1:
            # remove from monitor
            del tracking_tickers[symbol]
            print("[{}] Sell order <{}>[{}] filled".format(
                utils.get_now(), symbol, ticker_id))
            # update account status
            account_data = webullsdk.get_account()
            utils.save_webull_account(account_data)
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=PENDING_ORDER_TIMEOUT):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(
                        ticker['pending_order_id'], note="Sell order timeout, canceled!")
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
                            order_response['orderId'], note="Resubmit sell order.")
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
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(seconds=OBSERVE_TIMEOUT):
            print("[{}] Trading <{}>[{}] session timeout!".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del tracking_tickers[symbol]
            return

        # check if 3 continues loss trades and still in blacklist time
        if symbol in trading_stats and trading_stats[symbol]['continue_lose_trades'] >= 3 and (datetime.now() - trading_stats['symbol']['last_trade_time']) <= timedelta(seconds=BLACKLIST_TIMEOUT):
            print("[{}] <{}>[{}] all last 3 trade loss, waiting for blacklist timeout, stop trading!".format(
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

            # check if last sell time is too short compare current time
            if ticker['last_sell_time'] != None and (datetime.now() - ticker['last_sell_time']) < timedelta(seconds=TRADE_INTERVAL):
                print("[{}] Don't buy <{}>[{}] too quick after sold!".format(
                    utils.get_now(), symbol, ticker_id))
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
                    if quote == None or 'depth' not in quote:
                        return
                    ask_price = float(
                        quote['depth']['ntvAggAskList'][0]['price'])
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    gap = (ask_price - bid_price) / bid_price
                    if gap > MAX_BID_ASK_GAP:
                        print("[{}] <{}>[{}] gap too large, ask: {}, bid: {}, stop trading!".format(
                            utils.get_now(), symbol, ticker_id, ask_price, bid_price))
                        # remove from monitor
                        del tracking_tickers[symbol]
                        return
                    buy_position_amount = BUY_ORDER_LIMIT
                    # check win rate
                    if symbol in trading_stats:
                        win_rate = float(
                            trading_stats[symbol]['win_trades']) / trading_stats[symbol]['trades']
                        buy_position_amount = max(
                            BUY_ORDER_LIMIT * win_rate, BUY_ORDER_LIMIT * 0.3)
                    buy_quant = (int)(buy_position_amount / ask_price)
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
            tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate
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
            exit_note = None
            # stop loss for STOP_LOSS_RATE
            if profit_loss_rate <= STOP_LOSS_RATE:
                exit_note = "Stop loss {}%".format(
                    round(profit_loss_rate * 100, 2))
                exit_trading = True

            # check if holding too long
            if (datetime.now() - ticker['order_filled_time']) >= timedelta(seconds=HOLDING_ORDER_TIMEOUT) and profit_loss_rate < 0.01:
                print("[{}] Holding <{}>[{}] too long!".format(
                    utils.get_now(), symbol, ticker_id))
                exit_note = "Holding too long!"
                exit_trading = True

            if not exit_trading:
                # fetch 1m bar charts
                bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=20))

                # get bars error
                if bars.empty:
                    print("[{}] <{}>[{}] Bars data error!".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Bars data error!"
                    exit_trading = True

                # check if momentum is stop
                if not exit_trading and utils.check_bars_current_low_less_than_prev_low(bars):
                    print("[{}] <{}>[{}] Current low price is less than previous low price.".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Current Low < Previous Low."
                    exit_trading = True

                # check if price fixed in last 3 candles
                if not exit_trading and utils.check_bars_price_fixed(bars):
                    print("[{}] <{}>[{}] Price is fixed during last 3 candles.".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Price fixed during last 3 candles."
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
                # update trading stats
                if symbol in trading_stats:
                    trading_stats[symbol] = {
                        "trades": 0,
                        "win_trades": 0,
                        "lose_trades": 0,
                        "continue_lose_trades": 0,
                        "last_trade_time": None,
                    }
                trading_stats[symbol]['trades'] += 1
                trading_stats[symbol]['last_trade_time'] = datetime.now()
                if profit_loss_rate > 0:
                    trading_stats[symbol]['win_trades'] += 1
                    trading_stats[symbol]['continue_lose_trades'] = 0
                else:
                    trading_stats[symbol]['lose_trades'] += 1
                    trading_stats[symbol]['continue_lose_trades'] += 1

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
            # check gap change
            if change_percentage >= MIN_SURGE_CHANGE_PERCENTAGE:
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
                            "last_profit_loss_rate": None,
                            "last_sell_time": None,
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
    day_profit_loss = "-"
    if "dayProfitLoss" in portfolio:
        day_profit_loss = portfolio['dayProfitLoss']
    print("[{}] Today's P&L: {}".format(
        utils.get_now(), day_profit_loss))

    # webullsdk.logout()
    # print("[{}] Webull logged out".format(utils.get_now()))


if __name__ == "django.core.management.commands.shell":
    start()
