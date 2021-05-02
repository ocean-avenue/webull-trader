# -*- coding: utf-8 -*-

# fetch minute/daily historical candle data into database

def start():
    import time
    from datetime import date
    from sdk import webullsdk
    from scripts import utils
    from old_ross.models import TradingSettings, WebullOrder

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print("[{}] Cannot find trading settings, exit!".format(utils.get_now()))
        return

    webullsdk.login(paper=trading_settings.paper)

    today = date.today()
    # get all symbols orders in today's orders
    symbol_list = []
    ticker_id_list = []
    today_orders = WebullOrder.objects.filter(placed_time__year=str(
        today.year), placed_time__month=str(today.month), placed_time__day=str(today.day))
    for order in today_orders:
        symbol = order.symbol
        ticker_id = int(order.ticker_id)
        if symbol not in symbol_list:
            symbol_list.append(symbol)
            ticker_id_list.append(ticker_id)

    for i in range(0, len(symbol_list)):
        symbol = symbol_list[i]
        ticker_id = ticker_id_list[i]
        # fetch minute historical candle
        timestamp = int(time.time())
        minute_bar_list = []
        while timestamp:
            finish = False
            temp_bar_list = []
            bars = webullsdk.get_1m_bars(
                ticker_id=ticker_id, count=500, timestamp=timestamp)
            for index, bar in bars.iterrows():
                date_time = index.to_pydatetime()
                if today != date_time.date():
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
        # fetch daily historical candle
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

        print("[{}] Import minute bar for {}...".format(
            utils.get_now(), symbol))
        for bar_data in minute_bar_list:
            utils.save_hist_minute_bar(bar_data)

        print("[{}] Import daily bar for {}...".format(utils.get_now(), symbol))
        for bar_data in daily_bar_list:
            utils.save_hist_daily_bar(bar_data)

        # sleep for a while
        time.sleep(5)


if __name__ == "django.core.management.commands.shell":
    start()
