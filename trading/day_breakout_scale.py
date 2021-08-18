# -*- coding: utf-8 -*-

# Breakout day trading class, scale if reach add unit price

from datetime import datetime
from scripts import utils
from trading.day_breakout import DayTradingBreakout


class DayTradingBreakoutScale(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutScale"

    def check_scale_in(self, ticker, position):
        symbol = ticker['symbol']
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        last_buy_time = ticker['last_buy_time']
        target_units = 4
        units = 1
        position_obj = ticker['position_obj']
        if position_obj:
            target_units = position_obj.target_units
            units = position_obj.units
        # check if already reach target units
        if units >= target_units:
            utils.print_trading_log("Scale in <{}> position reject, already has {} units, unrealized P&L: {}%".format(
                symbol, units, round(profit_loss_rate * 100, 2)))
            return False
        # check if P&L > 5% and pass 5 minutes long
        if profit_loss_rate >= 0.05 and (datetime.now() - last_buy_time).seconds >= 300:
            utils.print_trading_log("Scale in <{}> position, unrealized P&L: {}%".format(
                symbol, round(profit_loss_rate * 100, 2)))
            return True
        return False

    def check_stop_profit(self, ticker, position):
        exit_trading = False
        exit_note = None
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        initial_cost = ticker['initial_cost']
        last_price = float(position['lastPrice'])
        if initial_cost and initial_cost > 0:
            profit_loss_rate = (last_price - initial_cost) / initial_cost
        if profit_loss_rate >= 1:
            exit_trading = True
            exit_note = "Home run at {}!".format(last_price)
        return (exit_trading, exit_note)

    def update_exit_period(self, ticker, position):
        symbol = ticker['symbol']
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        initial_cost = ticker['initial_cost']
        last_price = float(position['lastPrice'])
        if initial_cost and initial_cost > 0:
            profit_loss_rate = (last_price - initial_cost) / initial_cost
        current_exit_period = ticker['exit_period']
        if profit_loss_rate >= 0.9 and current_exit_period > 1:
            self.tracking_tickers[symbol]['exit_period'] = 1
        elif profit_loss_rate >= 0.7 and current_exit_period > 3:
            self.tracking_tickers[symbol]['exit_period'] = 3
        elif profit_loss_rate >= 0.5 and current_exit_period > 5:
            self.tracking_tickers[symbol]['exit_period'] = 5
        elif profit_loss_rate >= 0.3 and current_exit_period > 7:
            self.tracking_tickers[symbol]['exit_period'] = 7
