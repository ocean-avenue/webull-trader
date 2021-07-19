# -*- coding: utf-8 -*-

# Breakout day trading class, using ask price for entry

from trading.day_breakout import DayTradingBreakout
from sdk import webullsdk


class DayTradingBreakoutAsk(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutAsk"

    def get_buy_price(self, ticker):
        ticker_id = ticker['ticker_id']
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return None
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        if ask_price == None:
            return None
        return ask_price
