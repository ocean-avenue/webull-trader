# -*- coding: utf-8 -*-

# fetch minute/daily historical candle data into database


def start(day=None):
    import time
    import pandas as pd
    from datetime import date
    from sdk import webullsdk, fmpsdk, finvizsdk
    from common import utils, db
    from webull_trader.models import WebullOrder, SwingWatchlist

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
            bars: pd.DataFrame = webullsdk.get_1m_bars(
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
            if finish or bars.size == 0:
                timestamp = None
            else:
                timestamp = int(bars.index[0].timestamp()) - 1

        # save historical minute bar
        db.save_hist_minute_bar_list(minute_bar_list)

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
        db.save_hist_daily_bar_list(daily_bar_list)

        # fetch historical quote
        quote_data = webullsdk.get_quote(ticker_id=ticker_id)

        additional_quote_data = finvizsdk.get_quote(symbol)

        quote_data['shortFloat'] = additional_quote_data['shortFloat']

        # save historical quote
        db.save_hist_key_statistics(quote_data, day)

        # rest for 5 sec
        time.sleep(5)

    # fetch market statistics
    top_gainer_change = utils.get_avg_change_from_movers(
        webullsdk.get_top_gainers(count=5))
    pre_gainer_change = utils.get_avg_change_from_movers(
        webullsdk.get_pre_market_gainers(count=5))
    after_gainer_change = utils.get_avg_change_from_movers(
        webullsdk.get_after_market_gainers(count=5))
    top_loser_change = utils.get_avg_change_from_movers(
        webullsdk.get_top_losers(count=5))
    pre_loser_change = utils.get_avg_change_from_movers(
        webullsdk.get_pre_market_losers(count=5))
    after_loser_change = utils.get_avg_change_from_movers(
        webullsdk.get_after_market_losers(count=5))
    db.save_hist_market_statistics({
        'top_gainer_change': top_gainer_change,
        'pre_gainer_change': pre_gainer_change,
        'after_gainer_change': after_gainer_change,
        'top_loser_change': top_loser_change,
        'pre_loser_change': pre_loser_change,
        'after_loser_change': after_loser_change,
    }, day)

    algo_type = utils.get_algo_type()

    if utils.check_require_top_list_algo(algo_type):
        # save top gainers
        top_gainers = webullsdk.get_top_gainers(count=30)
        for gainer_data in top_gainers:
            symbol = gainer_data['symbol']
            ticker_id = gainer_data['ticker_id']
            db.save_hist_top_gainer(gainer_data, day)
            key_statistics = db.get_hist_key_stat(symbol, day)
            if not key_statistics:
                # fetch historical quote
                quote_data = webullsdk.get_quote(ticker_id=ticker_id)
                additional_quote_data = finvizsdk.get_quote(symbol)
                quote_data['shortFloat'] = additional_quote_data['shortFloat']
                # save historical quote
                db.save_hist_key_statistics(quote_data, day)

        # save top losers
        top_losers = webullsdk.get_top_losers(count=30)
        for loser_data in top_losers:
            symbol = loser_data['symbol']
            ticker_id = loser_data['ticker_id']
            db.save_hist_top_loser(loser_data, day)
            key_statistics = db.get_hist_key_stat(symbol, day)
            if not key_statistics:
                # fetch historical quote
                quote_data = webullsdk.get_quote(ticker_id=ticker_id)
                additional_quote_data = finvizsdk.get_quote(symbol)
                quote_data['shortFloat'] = additional_quote_data['shortFloat']
                # save historical quote
                db.save_hist_key_statistics(quote_data, day)

    if utils.is_swing_trade_algo(algo_type):
        # fetch watchlist symbol daily data
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
                db.save_swing_hist_daily_bar(bar_data)


if __name__ == "django.core.management.commands.shell":
    start()
