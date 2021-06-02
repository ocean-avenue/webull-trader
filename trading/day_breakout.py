# -*- coding: utf-8 -*-

# Breakout day trading class

import time
from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


class DayTradingBreakout(StrategyBase):

    def __init__(self, paper, entry_period=20, exit_period=10):
        super().__init__(paper=paper)
        self.entry_period = entry_period
        self.exit_period = exit_period

    def get_tag(self):
        return "DayTradingBreakout"

    def get_setup(self):
        return SetupType.DAY_20_MINUTES_NEW_HIGH

    def check_entry(self, ticker, bars):
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        # check if above vwap
        if current_price < current_candle['vwap']:
            return False
        period_bars = bars.head(len(bars) - 1).tail(self.entry_period)
        period_high_price = 0
        for _, row in period_bars.iterrows():
            close_price = row['close']
            if close_price > period_high_price:
                period_high_price = close_price
        # check if new high
        if current_price < period_high_price:
            return False
        # check if gap too large
        if period_high_price * 1.01 < current_price:
            self.print_log("<{}>[{}] new high price gap too large, new high: {}, period high: {}, no entry!".format(
                ticker['symbol'], ticker['ticker_id'], current_price, period_high_price))
            return False
        return True

    def check_stop_loss(self, ticker, position):
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        # stop loss for buy prev low
        if ticker['stop_loss'] and last_price < ticker['stop_loss']:
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        return (exit_trading, exit_note)

    def check_exit(self, ticker, bars):
        exit_trading = False
        exit_note = None
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        period_bars = bars.head(len(bars) - 1).tail(self.exit_period)
        period_low_price = 99999
        for _, row in period_bars.iterrows():
            close_price = row['close']
            if close_price < period_low_price:
                period_low_price = close_price
        # check if new low
        if current_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(self.exit_period)
            self.print_log("<{}>[{}] new period low price, new low: {}, period low: {}, exit!".format(
                ticker['symbol'], ticker['ticker_id'], current_price, period_low_price))
        # check if price fixed in last 3 candles
        elif utils.check_bars_price_fixed(bars):
            self.print_log(
                "<{}>[{}] Price is fixed during last 3 candles.".format(ticker['symbol'], ticker['ticker_id']))
            exit_trading = True
            exit_note = "Price fixed during last 3 candles."
        return (exit_trading, exit_note)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(seconds=self.observe_timeout_in_sec):
            self.print_log(
                "Trading <{}>[{}] session timeout!".format(symbol, ticker_id))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
            m2_bars = utils.convert_2m_bars(m1_bars)
            if m2_bars.empty:
                return

            if not utils.check_bars_updated(m2_bars):
                self.print_log(
                    "<{}>[{}] Charts is not updated, stop trading!".format(symbol, ticker_id))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            if not utils.check_bars_has_volume(m2_bars):
                self.print_log(
                    "<{}>[{}] Charts has not enough volume, stop trading!".format(symbol, ticker_id))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            # candle data
            current_candle = m2_bars.iloc[-1]
            prev_candle = m2_bars.iloc[-2]

            # check entry: current price above vwap, entry period minutes new high
            if self.check_entry(ticker, m2_bars):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None or 'depth' not in quote:
                    return
                ask_price = float(quote['depth']['ntvAggAskList'][0]['price'])
                buy_position_amount = self.get_buy_order_limit(symbol)
                buy_quant = (int)(buy_position_amount / ask_price)
                # submit limit order at ask price
                order_response = webullsdk.buy_limit_order(
                    ticker_id=ticker_id,
                    price=ask_price,
                    quant=buy_quant)
                self.print_log("Trading <{}>[{}], price: {}, vwap: {}, volume: {}".format(
                    symbol, ticker_id, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                self.print_log("🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                    symbol, ticker_id, buy_quant, ask_price))
                # update pending buy
                self.update_pending_buy_order(
                    symbol, order_response, stop_loss=prev_candle['low'])
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                self.print_log(
                    "Finding <{}>[{}] position error!".format(symbol, ticker_id))
                return

            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate

            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = self.tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                self.tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate

            # check stop loss
            exit_trading, exit_note = self.check_stop_loss(
                ticker, ticker_position)

            if not exit_trading:
                # get 2m bar charts
                m2_bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=30))

                # get bars error
                if m2_bars.empty:
                    self.print_log(
                        "<{}>[{}] Bars data error!".format(symbol, ticker_id))
                    exit_trading = True
                    exit_note = "Bars data error!"
                else:
                    # check exit trade
                    exit_trading, exit_note = self.check_exit(ticker, m2_bars)

            # exit trading
            if exit_trading:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = float(
                    quote['depth']['ntvAggBidList'][0]['price'])
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=holding_quantity)
                self.print_log("📈 Exit trading <{}>[{}] P&L: {}%".format(
                    symbol, ticker_id, round(profit_loss_rate * 100, 2)))
                self.print_log("🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    symbol, ticker_id, holding_quantity, bid_price))
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
            # init stats if not
            self.init_tracking_stats_if_not(ticker)
            # do trade
            self.trade(ticker)

        # find trading ticker in top gainers
        top_gainers = []
        if utils.is_regular_market_hour():
            top_gainers = webullsdk.get_top_gainers()
        elif utils.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif utils.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # self.print_log("Scanning top gainers [{}]...".format(
        #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            ticker_id = gainer["ticker_id"]
            # self.print_log("Scanning <{}>[{}]...".format(symbol, ticker_id))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= self.min_surge_change_ratio:
                # found trading ticker
                ticker = self.get_init_tracking_ticker(symbol, ticker_id)
                self.tracking_tickers[symbol] = ticker
                self.print_log(
                    "Found <{}>[{}] to trade!".format(symbol, ticker_id))
                # do trade
                self.trade(ticker)

    def on_end(self):
        self.trading_end = True
        # check if still holding any positions before exit
        while len(list(self.tracking_tickers)) > 0:
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                self.clear_position(ticker)

            # at least slepp 1 sec
            time.sleep(1)

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.get_trading_hour(), date.today())
