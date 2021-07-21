# -*- coding: utf-8 -*-

# fetch minute/daily historical candle data into database


def start(day=None):
    import time
    from datetime import date
    from sdk import webullsdk, fmpsdk, finvizsdk
    from scripts import utils
    from webull_trader.models import WebullOrder, SwingWatchlist, SwingPosition, SwingTrade, OvernightPosition, OvernightTrade
    from webull_trader.enums import ActionType

    if day == None:
        day = date.today()
    all_day_orders = WebullOrder.objects.filter(filled_time__year=str(
        day.year), filled_time__month=str(day.month), filled_time__day=str(day.day))
    # get all symbols orders in today's orders
    symbol_list = []
    ticker_id_list = []
    for order in all_day_orders:
        symbol = order.symbol
        ticker_id = int(order.ticker_id)
        if symbol not in symbol_list:
            symbol_list.append(symbol)
            ticker_id_list.append(ticker_id)

    # fetch stock quotes
    utils.fetch_stock_quotes(symbol_list)

    # iterate through all symbol
    for i in range(0, len(symbol_list)):
        symbol = symbol_list[i]
        ticker_id = ticker_id_list[i]
        # fetch historical minute bar
        timestamp = int(time.time())
        minute_bar_list = []
        while timestamp:
            finish = False
            temp_bar_list = []
            bars = webullsdk.get_1m_bars(
                ticker_id=ticker_id, count=500, timestamp=timestamp)
            for index, bar in bars.iterrows():
                date_time = index.to_pydatetime()
                if day != date_time.date():
                    finish = True
                else:
                    temp_bar_list.append({
                        'symbol': symbol,
                        'date': date_time.date(),
                        'time': date_time,
                        'open': bar['open'],
                        'high': bar['high'],
                        'low': bar['low'],
                        'close': bar['close'],
                        'volume': bar['volume'],
                        'vwap': bar['vwap'],
                    })
            minute_bar_list = temp_bar_list + minute_bar_list
            # reset temp list
            temp_bar_list = []
            if finish:
                timestamp = None
            else:
                timestamp = int(bars.index[0].timestamp()) - 1

        # save historical minute bar
        utils.save_hist_minute_bar_list(minute_bar_list)

        # fetch historical daily bar
        daily_bar_list = []
        bars = webullsdk.get_1d_bars(ticker_id=ticker_id, count=60)
        for index, bar in bars.iterrows():
            daily_bar_list.append({
                'symbol': symbol,
                'date': index.to_pydatetime().date(),
                'open': bar['open'],
                'high': bar['high'],
                'low': bar['low'],
                'close': bar['close'],
                'volume': bar['volume'],
            })

        # save historical daily bar
        utils.save_hist_daily_bar_list(daily_bar_list)

        # fetch historical quote
        quote_data = webullsdk.get_quote(ticker_id=ticker_id)

        additional_quote_data = finvizsdk.get_quote(symbol)

        quote_data['shortFloat'] = additional_quote_data['shortFloat']

        # save historical quote
        utils.save_hist_key_statistics(quote_data, day)

        # rest for 5 sec
        time.sleep(5)

    # save top gainers
    top_gainers = webullsdk.get_top_gainers(count=30)
    for gainer_data in top_gainers:
        symbol = gainer_data['symbol']
        ticker_id = gainer_data['ticker_id']
        utils.save_hist_top_gainer(gainer_data, day)
        key_statistics = utils.get_hist_key_stat(symbol, day)
        if not key_statistics:
            # fetch historical quote
            quote_data = webullsdk.get_quote(ticker_id=ticker_id)
            additional_quote_data = finvizsdk.get_quote(symbol)
            quote_data['shortFloat'] = additional_quote_data['shortFloat']
            # save historical quote
            utils.save_hist_key_statistics(quote_data, day)

    # save top losers
    top_losers = webullsdk.get_top_losers(count=30)
    for loser_data in top_losers:
        symbol = loser_data['symbol']
        ticker_id = loser_data['ticker_id']
        utils.save_hist_top_loser(loser_data, day)
        key_statistics = utils.get_hist_key_stat(symbol, day)
        if not key_statistics:
            # fetch historical quote
            quote_data = webullsdk.get_quote(ticker_id=ticker_id)
            additional_quote_data = finvizsdk.get_quote(symbol)
            quote_data['shortFloat'] = additional_quote_data['shortFloat']
            # save historical quote
            utils.save_hist_key_statistics(quote_data, day)

    # fetch watchlist symbol daily data
    algo_type = utils.get_algo_type()
    if utils.check_swing_trade_algo(algo_type):
        swing_watchlist = SwingWatchlist.objects.all()
        for swing_watch in swing_watchlist:
            symbol = swing_watch.symbol
            try:
                # fetch sma 120
                hist_sma120 = fmpsdk.get_daily_sma(symbol, 120)
                # fetch sma 55
                hist_sma55 = fmpsdk.get_daily_sma(symbol, 55)
                # fetch rsi 10
                hist_rsi10 = fmpsdk.get_daily_rsi(symbol, 10)
            except:
                print("[{}] Fetch daily data for <{}> error!".format(
                    utils.get_now(), symbol))
                continue
            print("[{}] Insert daily data for <{}>...".format(
                utils.get_now(), symbol))
            # insert 120 days data
            sma120_120_days = hist_sma120[0:120][::-1]
            sma55_120_days = hist_sma55[0:120][::-1]
            rsi10_120_days = hist_rsi10[0:120][::-1]
            for i in range(0, len(sma120_120_days)):
                sma120_data = sma120_120_days[i]
                sma55_data = sma55_120_days[i]
                rsi10_data = rsi10_120_days[i]
                bar_data = {
                    'symbol': symbol,
                    'date': sma120_data['date'],
                    'open': sma120_data['open'],
                    'high': sma120_data['high'],
                    'low': sma120_data['low'],
                    'close': sma120_data['close'],
                    'volume': sma120_data['volume'],
                    'sma_120': sma120_data['sma'],
                    'sma_55': sma55_data['sma'],
                    'rsi_10': rsi10_data['rsi'],
                }
                utils.save_swing_hist_daily_bar(bar_data)

    # adjust swing position data by filled order
    swing_positions = SwingPosition.objects.filter(require_adjustment=True)
    for swing_position in swing_positions:
        symbol = swing_position.symbol
        N = utils.get_avg_true_range(symbol)
        order_ids = swing_position.order_ids.split(',')
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
                add_unit_price = round(webull_order.avg_price + N / 2, 2)
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
            # fill webull order setup
            webull_order.setup = setup
            webull_order.save()
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

    for order in all_day_orders:
        # check overnight position
        overnight_position = OvernightPosition.objects.filter(
            order_id=order.order_id).first()
        if overnight_position:
            overnight_position.cost = order.avg_price
            overnight_position.quantity = order.filled_quantity
            overnight_position.buy_time = order.filled_time
            overnight_position.buy_date = order.filled_time.date()
            # save
            overnight_position.save()
            # fill order setup
            order.setup = overnight_position.setup
            order.save()
            continue

        # check overnight trade
        overnight_trade = OvernightTrade.objects.filter(
            sell_order_id=order.order_id).first()
        if overnight_trade:
            overnight_trade.sell_price = order.avg_price
            overnight_trade.quantity = order.filled_quantity
            overnight_trade.sell_time = order.filled_time
            overnight_trade.sell_date = order.filled_time.date()
            # save
            overnight_trade.save()
            # fill order setup
            order.setup = overnight_trade.setup
            order.save()
            continue


if __name__ == "django.core.management.commands.shell":
    start()
