# -*- coding: utf-8 -*-

# Breakout day trading class, scale if reach add unit price and use period high as ROC check

from scripts import config
from trading.day_breakout_scale import DayTradingBreakoutScale


class DayTradingBreakoutScalePeriodROC(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScalePeriodROC"

    def get_price_rate_of_change(bars, period=10):
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(int(period / 2))
        period_high_price = 0.1
        for _, row in period_bars.iterrows():
            price = row["close"]
            if price > period_high_price:
                period_high_price = price
        prev_price = bars.iloc[-2]['close']
        # if prev price is highest, no ROC required
        if prev_price > period_high_price:
            return config.DAY_PRICE_RATE_OF_CHANGE + 1
        current_price = bars.iloc[-1]['close']
        ROC = (current_price - period_high_price) / period_high_price * 100
        return ROC
