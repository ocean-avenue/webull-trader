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

    # TODO
    # today = date.today()
    today = date(2021, 4, 30)
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

    # fetch minute historical candle
    for i in range(0, len(symbol_list)):
        symbol = symbol_list[i]
        ticker_id = ticker_id_list[i]
        timestamp = int(time.time())
        candle_list = []
        while timestamp:
            finish = False
            temp_candle_list = []
            bars = webullsdk.get_1m_bars(
                ticker_id=ticker_id, count=500, timeStamp=timestamp)
            for index, bar in bars.iterrows():
                date_time = index.to_pydatetime()
                if today != date_time.date():
                    finish = True
                else:
                    temp_candle_list.append({
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
            candle_list = temp_candle_list + candle_list
            temp_candle_list = []
            if finish:
                timestamp = None
            else:
                timestamp = int(bars.index[0].timestamp()) - 1
        # sleep for a while
        time.sleep(5)


if __name__ == "django.core.management.commands.shell":
    start()
