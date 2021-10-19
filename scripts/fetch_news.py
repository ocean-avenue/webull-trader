# -*- coding: utf-8 -*-

# fetch news data for stock into database

def start(day=None):
    import time
    from datetime import date
    from sdk import webullsdk
    from common import utils
    from webull_trader.models import WebullOrder

    # paper = utils.check_paper()
    # webullsdk.login(paper=paper)

    if day == None:
        day = date.today()
    # get all symbols orders in today's orders
    symbol_list = []
    ticker_id_list = []
    today_orders = WebullOrder.objects.filter(placed_time__year=str(
        day.year), placed_time__month=str(day.month), placed_time__day=str(day.day))
    for order in today_orders:
        symbol = order.symbol
        ticker_id = int(order.ticker_id)
        if symbol not in symbol_list:
            symbol_list.append(symbol)
            ticker_id_list.append(ticker_id)

    # iterate through all symbol
    for i in range(0, len(symbol_list)):
        symbol = symbol_list[i]

        # fetch webull news
        news_list = webullsdk.get_news(stock=symbol)

        # save webull news
        utils.save_webull_news_list(news_list, symbol, day)

        # rest for 5 sec
        time.sleep(5)


if __name__ == "django.core.management.commands.shell":
    start()
