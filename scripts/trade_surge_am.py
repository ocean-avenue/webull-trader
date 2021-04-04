# -*- coding: utf-8 -*-

TRADED_SYMBOLS = []
MIN_SURGE_AMOUNT = 21000
MIN_SURGE_VOL = 1000
SURGE_MIN_CHANGE_PERCENTAGE = 8  # at least 8% change for surge
TRADE_TIMEOUT = 6  # trading time out in minutes


def start():
    import time
    from datetime import datetime, timedelta
    from sdk import webullsdk

    global TRADED_SYMBOLS
    global MIN_SURGE_AMOUNT
    global MIN_SURGE_VOL
    global SURGE_MIN_CHANGE_PERCENTAGE
    global TRADE_TIMEOUT

    def _get_now():
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _is_after_market():
        now = datetime.now()
        if now.hour < 13 or now.hour >= 17:
            return False
        return True

    trading_ticker = None

    # https://school.stockcharts.com/doku.php?id=technical_indicators:moving_averages
    def _calculate_ema9(charts):
        multiplier = 2 / (9 + 1)
        charts_length = len(charts)
        for i in range(0, charts_length):
            candle = charts[charts_length - i - 1]
            if i < 8:
                candle['ema9'] = 0
            elif i == 8:
                # use sma for initial ema
                sum = 0.0
                for j in (0, 8):
                    c = charts[charts_length - j - 1]
                    sum += c['close']
                candle['ema9'] = round(sum / 9, 2)
            else:
                prev_candle = charts[charts_length - i]
                candle['ema9'] = round(
                    (candle['close'] - prev_candle['ema9']) * multiplier + prev_candle['ema9'], 2)
        return charts

    def _trade(charts):

        # check timeout, skip this ticker if no trade during last 6 minutes
        now_time = datetime.now()
        if trading_ticker['holding_quantity'] == 0 and (now_time - trading_ticker['start_time']) >= timedelta(minutes=TRADE_TIMEOUT):
            return True
        # calculate and fill ema 9 data
        _calculate_ema9(charts)
        current_candle = charts[0]
        prev_candle = charts[1]
        # check low price above vwap and ema 9
        if current_candle['low'] > current_candle['vwap'] and current_candle['low'] > current_candle['ema9']:
            # check first candle make new high
            # TODO
            pass
        # TODO, buy after the first pull back
        # TODO, take profit along the way (sell half, half, half...)
        return False

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
                            "holding_quantity": 0,
                        }
                        TRADED_SYMBOLS.append(symbol)
                        print("[{}] found <{}> to trade with...".format(
                            _get_now(), symbol))
                        if _trade(charts):
                            trading_ticker = None

        time.sleep(5)


if __name__ == "django.core.management.commands.shell":
    start()