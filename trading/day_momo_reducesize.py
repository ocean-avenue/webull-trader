# -*- coding: utf-8 -*-

# Momo day trading based on win rate, reduce size if win rate is low

from datetime import datetime, timedelta
from trading.day_momo import DayTradingMomo
from scripts import config


class DayTradingMomoReduceSize(DayTradingMomo):

    def get_tag(self):
        return "DayTradingMomoReduceSize"

    def get_buy_order_limit(self, symbol):
        buy_position_amount = self.extended_order_amount_limit
        if self.is_regular_market_hour():
            buy_position_amount = self.order_amount_limit
        # check win rate
        if symbol in self.tracking_stats:
            win_rate = float(
                self.tracking_stats[symbol]['win_trades']) / self.tracking_stats[symbol]['trades']
            buy_position_amount = max(
                self.order_amount_limit * win_rate, self.order_amount_limit * 0.3)
        return buy_position_amount

    def check_if_track_symbol(self, symbol):
        # # check if sell not long ago
        # if symbol in self.tracking_stats and (datetime.now() - self.tracking_stats[symbol]['last_trade_time']) <= timedelta(seconds=100):
        #     return False
        # check if 3 continues loss trades and still in blacklist time
        if symbol in self.tracking_stats and self.tracking_stats[symbol]['continue_lose_trades'] >= 3 and (datetime.now() - self.tracking_stats[symbol]['last_trade_time']) <= timedelta(seconds=config.BLACKLIST_TIMEOUT_IN_SEC):
            return False
        return True
