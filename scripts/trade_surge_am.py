# -*- coding: utf-8 -*-

TRADED_SYMBOLS = []
MIN_SURGE_AMOUNT = 21000
MIN_SURGE_VOL = 1000
SURGE_MIN_CHANGE_PERCENTAGE = 8  # at least 8% change for surge


def start():
    import time
    from datetime import datetime, timedelta
    from sdk import webullsdk

    global TRADED_SYMBOLS
    global MIN_SURGE_AMOUNT
    global MIN_SURGE_VOL
    global SURGE_MIN_CHANGE_PERCENTAGE

    def _is_after_market():
        now = datetime.now()
        if now.hour < 13 or now.hour >= 17:
            return False
        return True

    def _trade(charts):
        return False

    trading_ticker = None
    while _is_after_market():
        if trading_ticker:
            # already found trading ticker
            ticker_id = trading_ticker["ticker_id"]
            charts = webullsdk.get_quote_1m_charts(ticker_id)
            if _trade(charts):
                trading_ticker = None
        else:
            # find trading ticker in top gainers
            top_gainers = webullsdk.get_after_market_gainers()
            top_10_gainers = top_gainers[:10]

            for gainer in top_10_gainers:
                symbol = gainer["symbol"]
                ticker_id = gainer["ticker_id"]
                if symbol in TRADED_SYMBOLS:
                    continue
                change_percentage = gainer["change_percentage"]
                # check if change >= 8%
                if change_percentage * 100 >= SURGE_MIN_CHANGE_PERCENTAGE:
                    charts = webullsdk.get_quote_1m_charts(ticker_id)
                    latest_chart = charts[0]
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
                        TRADED_SYMBOLS.append(symbol)
                        if _trade(charts):
                            trading_ticker = None

        time.sleep(1)


if __name__ == "django.core.management.commands.shell":
    start()