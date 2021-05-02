# -*- coding: utf-8 -*-

# fetch minute/daily historical candle data into database

def start():
    from datetime import datetime
    from sdk import webullsdk
    from scripts import utils
    from old_ross.models import TradingSettings, WebullOrder

    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        print("[{}] Cannot find trading settings, exit!".format(utils.get_now()))
        return

    webullsdk.login(paper=trading_settings.paper)

    # TODO
    # today = datetime.today()
    today = datetime(2021, 4, 30)
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
        timestamp = None
        candle_list = []
        while True:
            finish = False
            temp_candle_list = []
            bars = webullsdk.get_1m_bars(ticker_id=ticker_id, count=500)
            for index, bar in bars.iterrows():
                datetime = index.to_pydatetime()
                # TODO


if __name__ == "django.core.management.commands.shell":
    start()
