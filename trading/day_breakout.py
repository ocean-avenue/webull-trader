# -*- coding: utf-8 -*-

# Breakout day trading class

from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils, config


class DayTradingBreakout(StrategyBase):

    import pandas as pd

    def __init__(self, paper, trading_hour, entry_period=20, exit_period=10, time_scale=1):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.time_scale = time_scale

    def get_tag(self):
        return "DayTradingBreakout"

    def get_setup(self):
        if self.entry_period == 30:
            return SetupType.DAY_30_CANDLES_NEW_HIGH
        elif self.entry_period == 20:
            return SetupType.DAY_20_CANDLES_NEW_HIGH
        return SetupType.DAY_10_CANDLES_NEW_HIGH

    # check if track in extended hour
    def check_surge(self, ticker, bar):
        close = bar["close"]
        vwap = bar["vwap"]
        volume = int(bar["volume"])
        if close * volume >= config.MIN_SURGE_AMOUNT and volume >= config.MIN_SURGE_VOLUME and close > vwap:
            utils.print_trading_log(
                "Found <{}> to trade!".format(ticker["symbol"]))
            return True
        return False

    def check_entry(self, ticker, bars):
        symbol = ticker["symbol"]
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        # check if above vwap
        if current_price <= current_candle['vwap']:
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
        if not self.check_if_trade_price_new_high(symbol, current_price):
            return False

        # check ema 9
        if current_price < current_candle['ema9']:
            utils.print_trading_log(
                "<{}> price is not above ema9, no entry!".format(symbol))
            return False

        # # check if gap already too large
        # if period_high_price * config.PERIOD_HIGH_PRICE_GAP_RATIO < current_price:
        #     utils.print_trading_log("<{}> new high price gap too large, new high: {}, period high: {}, no entry!".format(
        #         ticker['symbol'], current_price, period_high_price))
        #     return False

        if self.is_regular_market_hour() and not utils.check_bars_updated(bars):
            utils.print_trading_log(
                "<{}> candle chart is not updated, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if self.is_regular_market_hour() and not utils.check_bars_continue(bars, time_scale=self.time_scale):
            utils.print_trading_log(
                "<{}> candle chart is not continue, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if self.is_regular_market_hour() and  \
                not utils.check_bars_has_amount(bars, time_scale=self.time_scale, period=5) and \
                not utils.check_bars_amount_grinding(bars, period=5) and not utils.check_bars_rel_volume(bars):
            # has no volume and no relative volume
            utils.print_trading_log(
                "<{}> candle chart has not enough amount and volume, no entry!".format(symbol))
            return False

        if self.is_regular_market_hour() and not utils.check_bars_volatility(bars):
            utils.print_trading_log(
                "<{}> candle chart is not volatility, no entry!".format(symbol))
            return False

        if utils.check_bars_has_long_wick_up(bars, period=5):
            # has long wick up
            utils.print_trading_log(
                "<{}> candle chart has long wick up, no entry!".format(symbol))
            return False

        ROC = utils.get_bars_price_rate_of_change(
            bars, period=self.entry_period)
        if ROC <= config.DAY_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            utils.print_trading_log(
                "<{}> candle chart price rate of change for {} period is weak [{}], no entry!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        if symbol in self.tracking_stats:
            last_trade_time = self.tracking_stats[symbol]['last_trade_time']
            if last_trade_time and (datetime.now() - last_trade_time) <= timedelta(seconds=config.TRADE_INTERVAL_IN_SEC * self.time_scale):
                utils.print_trading_log(
                    "<{}> try buy too soon after last sell, no entry!".format(symbol))
                return False

        return True

    def check_stop_loss(self, ticker, bars):
        exit_trading = False
        exit_note = None
        # last formed candle
        last_candle = bars.iloc[-2]
        last_price = last_candle['close']
        # check stop loss
        if ticker['stop_loss'] and last_price < ticker['stop_loss']:
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        return (exit_trading, exit_note)

    def check_exit(self, ticker, bars):
        symbol = ticker['symbol']
        exit_trading = False
        exit_note = None
        # last formed candle
        last_candle = bars.iloc[-2]
        last_price = last_candle['close']
        period_bars = bars.head(len(bars) - 2).tail(self.exit_period)
        period_low_price = 99999
        for _, row in period_bars.iterrows():
            close_price = row['close']
            if close_price < period_low_price:
                period_low_price = close_price
        # check if new low
        if last_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(self.exit_period)
            utils.print_trading_log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, last_price, period_low_price))
        # check if has long wick up
        elif utils.check_bars_has_long_wick_up(bars, period=10):
            utils.print_trading_log(
                "<{}> candle chart has long wick up, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart has long wick up."
        # check if bar chart has volatility
        elif not utils.check_bars_volatility(bars):
            utils.print_trading_log(
                "<{}> candle chart is not volatility, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is not volatility."

        return (exit_trading, exit_note)

    def check_if_trade_price_new_high(self, symbol, price):
        return True

    def trade(self, ticker, m1_bars=pd.DataFrame()):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit_count=50)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(seconds=config.OBSERVE_TIMEOUT_IN_SEC):
            utils.print_trading_log(
                "Trading <{}> session timeout!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            if m1_bars.empty:
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.entry_period*self.time_scale+5))
            if m1_bars.empty:
                return
            bars = m1_bars
            if self.time_scale == 5:
                bars = utils.convert_5m_bars(m1_bars)

            # calculate and fill ema 9 data
            bars['ema9'] = bars['close'].ewm(span=9, adjust=False).mean()

            # candle data
            current_candle = bars.iloc[-1]
            prev_candle = bars.iloc[-2]

            # check entry: current price above vwap, entry period minutes new high
            if self.check_entry(ticker, bars):
                usable_cash = webullsdk.get_usable_cash()
                buy_position_amount = self.get_buy_order_limit(symbol)
                if usable_cash <= buy_position_amount:
                    utils.print_trading_log(
                        "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
                    return
                buy_price = self.get_buy_price(ticker)
                if buy_price == None:
                    return
                buy_quant = (int)(buy_position_amount / buy_price)
                if buy_quant > 0:
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=buy_price,
                        quant=buy_quant)
                    utils.print_trading_log("Trading <{}>, price: {}, vwap: {}, volume: {}".format(
                        symbol, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                    utils.print_trading_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                        symbol, buy_quant, buy_price))
                    # use min of (ask price, prev candle middle)
                    stop_loss = min(round(
                        (prev_candle['high'] + prev_candle['low']) / 2, 2), round(buy_price * 0.98, 2))
                    # update pending buy
                    self.update_pending_buy_order(
                        symbol, order_response, stop_loss=stop_loss)
                else:
                    utils.print_trading_log(
                        "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                utils.print_trading_log(
                    "Finding <{}> position error!".format(symbol))
                return
            if holding_quantity <= 0:
                # position is negitive, some unknown error happen
                utils.print_trading_log("<{}> holding quantity is negitive {}!".format(
                    symbol, holding_quantity))
                del self.tracking_tickers[symbol]
                return

            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate

            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = self.tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                self.tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate

            # get 1m bar charts
            m1_bars = webullsdk.get_1m_bars(
                ticker_id, count=(self.exit_period*self.time_scale+5))

            # get bars error
            if m1_bars.empty:
                utils.print_trading_log(
                    "<{}> bars data error!".format(symbol))
                exit_trading = True
                exit_note = "Bars data error!"
            else:
                # convert bars
                bars = m1_bars
                if self.time_scale == 5:
                    bars = utils.convert_5m_bars(m1_bars)
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(ticker, bars)
                # check exit trading
                if not exit_trading:
                    utils.print_trading_log("Checking exit for <{}>, unrealized P&L: {}%".format(
                        symbol, round(profit_loss_rate * 100, 2)))
                    # check exit trade
                    exit_trading, exit_note = self.check_exit(ticker, bars)

            # exit trading
            if exit_trading:
                sell_price = self.get_sell_price(ticker)
                if sell_price == None:
                    return
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=sell_price,
                    quant=holding_quantity)
                utils.print_trading_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                utils.print_trading_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, sell_price))
                # update pending sell
                self.update_pending_sell_order(
                    symbol, order_response, exit_note=exit_note)
                # update trading stats
                self.update_trading_stats(symbol, float(ticker_position['lastPrice']), float(
                    ticker_position['costPrice']), profit_loss_rate)

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if self.is_regular_market_hour():
            top_gainers = webullsdk.get_top_gainers()
        elif self.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif self.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # utils.print_trading_log("Scanning top gainers <{}>...".format(
        #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            ticker_id = gainer["ticker_id"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            # init tracking ticker
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            # check if can trade with requirements
            if not self.check_can_trade_ticker(ticker):
                continue
            # utils.print_trading_log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
                if self.is_extended_market_hour():
                    m1_bars = webullsdk.get_1m_bars(
                        ticker_id, count=(self.entry_period*self.time_scale+5))
                    if m1_bars.empty:
                        continue
                    # use latest 2 candle
                    latest_candle = m1_bars.iloc[-1]
                    latest_candle2 = m1_bars.iloc[-2]
                    # check if trasaction amount and volume meets requirement
                    if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                        # found trading ticker
                        self.tracking_tickers[symbol] = ticker
                        # do trade
                        self.trade(ticker, m1_bars=m1_bars)
                elif self.is_regular_market_hour():
                    # found trading ticker
                    self.tracking_tickers[symbol] = ticker
                    utils.print_trading_log(
                        "Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

        # save trading logs
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())
