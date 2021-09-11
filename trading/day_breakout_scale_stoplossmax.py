# -*- coding: utf-8 -*-

# Breakout day trading class, scale if reach add unit price and max stop loss

from scripts import config
from trading.day_breakout_scale import DayTradingBreakoutScale


class DayTradingBreakoutScaleStopLossMax(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScaleStopLossMax"

    def get_stop_loss_price(self, buy_price, bars):
        # use max stop loss
        return round(buy_price * (1 - config.MAX_DAY_STOP_LOSS), 2)
