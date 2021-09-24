# -*- coding: utf-8 -*-

from datetime import datetime
from scripts import utils, config
from trading.day_breakout import DayTradingBreakout


# Breakout day trading class, scale if reach add unit price

class DayTradingBreakoutScale(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutScale"

    def check_scale_in(self, ticker, bars, position):
        symbol = ticker['symbol']
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        last_buy_time = ticker['last_buy_time']
        target_units = 4
        units = 1
        position_obj = ticker['position_obj']
        if position_obj:
            target_units = position_obj.target_units
            units = position_obj.units
        # check if already reach target units
        if units >= target_units:
            return False
        # check if pass 5 minutes from initial buy or 1 minute from last buy
        trade_interval_sec = 60
        if units == 1:
            # give some time for trading to work out
            trade_interval_sec = 300
        if (datetime.now() - last_buy_time).seconds <= trade_interval_sec:
            return False
        # check if has 5% gain already
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate < 0.05:
            return False
        period_bars = bars.head(len(bars) - 1).tail(self.entry_period)
        period_high_price = 0
        for _, row in period_bars.iterrows():
            close_price = row['close']  # use close price
            if close_price > period_high_price:
                period_high_price = close_price
        # check if new high
        if current_price < period_high_price:
            return False

        if self.is_regular_market_hour() and not utils.check_bars_updated(bars):
            utils.print_trading_log(
                "<{}> candle chart is not updated, stop scale in!".format(symbol))
            return False

        if self.is_regular_market_hour() and not utils.check_bars_continue(bars, time_scale=self.time_scale):
            utils.print_trading_log(
                "<{}> candle chart is not continue, stop scale in!".format(symbol))
            return False

        if not utils.check_bars_has_amount(bars, time_scale=self.time_scale, period=2):
            # has no volume and amount
            utils.print_trading_log(
                "<{}> candle chart has not enough amount, no scale in!".format(symbol))
            return False

        # if self.is_regular_market_hour() and  \
        #         not utils.check_bars_rel_volume(bars) and not utils.check_bars_all_green(bars, period=5) and \
        #         not utils.check_bars_amount_grinding(bars, period=5):
        #     # has no volume and no relative volume
        #     utils.print_trading_log(
        #         "<{}> candle chart has no relative volume, no scale in!".format(symbol))
        #     return False

        ROC = self.get_price_rate_of_change(bars, period=self.entry_period)
        if ROC <= config.DAY_SCALE_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            utils.print_trading_log(
                "<{}> candle chart price rate of change for {} period ({}) is weak, no scale in!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        utils.print_trading_log("Scale in <{}> position".format(symbol))
        return True

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
        current_exit_period = ticker['exit_period'] or 1
        # if profit_loss_rate >= 0.9 and current_exit_period > 1:
        #     self.tracking_tickers[symbol]['exit_period'] = 1
        # elif profit_loss_rate >= 0.7 and current_exit_period > 3:
        #     self.tracking_tickers[symbol]['exit_period'] = 3
        if profit_loss_rate >= 0.5 and current_exit_period > 5:
            self.tracking_tickers[symbol]['exit_period'] = 5
        elif profit_loss_rate >= 0.3 and current_exit_period > 7:
            self.tracking_tickers[symbol]['exit_period'] = 7


# Breakout day trading class, scale if reach add unit price and max stop loss

class DayTradingBreakoutScaleStopLossMax(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScaleStopLossMax"

    def get_stop_loss_price(self, buy_price, bars):
        # use max stop loss
        return round(buy_price * (1 - config.MAX_DAY_STOP_LOSS), 2)


# Breakout day trading class, scale if reach add unit price and use average true range as stop loss

class DayTradingBreakoutScaleStopLossATR(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScaleStopLossATR"

    def get_stop_loss_price(self, buy_price, bars):

        N = utils.get_day_avg_true_range(bars)
        atr_stop_loss_price = round(buy_price - N, 2)

        prev_candle = bars.iloc[-2]
        # use max( min( prev candle middle, buy price -2% ), buy price -5% )
        stop_loss_price = max(
            min(round((prev_candle['high'] + prev_candle['low']) / 2, 2),
                round(buy_price * (1 - config.MIN_DAY_STOP_LOSS), 2)),
            round(buy_price * (1 - config.MAX_DAY_STOP_LOSS), 2))

        return max(atr_stop_loss_price, stop_loss_price)

    def get_scale_stop_loss_price(self, buy_price, bars):
        # N = utils.get_day_avg_true_range(bars)
        # return round(buy_price - N, 2)
        return None


# Breakout day trading class, scale if reach add unit price and use period high as ROC check

class DayTradingBreakoutScalePeriodROC(DayTradingBreakoutScale):

    def get_tag(self):
        return "DayTradingBreakoutScalePeriodROC"

    def get_price_rate_of_change(self, bars, period=10):
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
