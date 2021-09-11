# -*- coding: utf-8 -*-

# Breakout day trading class, scale if reach add unit price and use average true range as stop loss

from scripts import utils
from trading.day_breakout_scale import DayTradingBreakoutScale


class DayTradingBreakoutScaleStopLossATR(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScaleStopLossATR"

    def get_stop_loss_price(self, buy_price, bars):
        N = utils.get_day_avg_true_range(bars)
        return round(buy_price - N, 2)
