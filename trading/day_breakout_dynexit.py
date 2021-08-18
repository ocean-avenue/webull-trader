# -*- coding: utf-8 -*-

# Breakout day trade, adjust exit period by profit & loss rate.

from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutDynExit(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutDynExit"

    def update_exit_period(self, ticker, position):
        symbol = ticker['symbol']
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate >= 0.9:
            self.tracking_tickers[symbol]['exit_period'] = 1
        elif profit_loss_rate >= 0.7:
            self.tracking_tickers[symbol]['exit_period'] = 3
        elif profit_loss_rate >= 0.5:
            self.tracking_tickers[symbol]['exit_period'] = 5
        elif profit_loss_rate >= 0.3:
            self.tracking_tickers[symbol]['exit_period'] = 7