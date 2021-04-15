from datetime import datetime


def get_now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def is_after_market():
    # NY after market hour from 16:00 to 20:00
    now = datetime.now()
    if now.hour < 16 or now.hour >= 20:
        return False
    # wait 30 second for webull get after market data ready
    if now.hour == 16 and now.minute == 0 and now.second < 30:
        return False
    return True

# https://school.stockcharts.com/doku.php?id=technical_indicators:moving_averages


def calculate_charts_ema9(charts):
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
