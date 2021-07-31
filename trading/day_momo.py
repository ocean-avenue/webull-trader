# -*- coding: utf-8 -*-

# Momo day trading class

import time
from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils, config


class DayTradingMomo(StrategyBase):

    import pandas as pd

    def get_tag(self):
        return "DayTradingMomo"

    def get_setup(self):
        return SetupType.DAY_FIRST_CANDLE_NEW_HIGH

    def check_track(self, bar):
        close = bar["close"]
        vwap = bar["vwap"]
        volume = int(bar["volume"])
        if close * volume >= config.MIN_SURGE_AMOUNT and volume >= config.MIN_SURGE_VOLUME and close >= vwap:
            return True
        return False

    def check_entry(self, ticker, bars):
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        # current price data
        current_price = current_candle['close']
        # check current price above vwap, ema9 and first candle make new high
        if current_price > current_candle['vwap'] and current_price > current_candle['ema9'] \
                and current_candle['high'] > prev_candle['high'] \
                and self.check_if_trade_price_new_high(ticker, current_price):
            return True
        return False

    def check_stop_loss(self, ticker, position):
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        # stop loss for buy prev low
        if ticker['stop_loss'] and last_price < ticker['stop_loss']:
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        # stop loss for stop_loss_ratio
        elif profit_loss_rate <= self.stop_loss_ratio:
            exit_note = "Stop loss for {}%".format(
                round(profit_loss_rate * 100, 2))
            exit_trading = True
        return (exit_trading, exit_note)

    def check_exit(self, ticker, bars):
        exit_trading = False
        exit_note = None
        # check if momentum is stop
        if utils.check_bars_current_low_less_than_prev_low(bars):
            utils.print_trading_log("<{}> current low price is less than previous low price.".format(
                ticker['symbol']))
            exit_trading = True
            exit_note = "Current Low < Previous Low."
        # check if price fixed in last 3 candles
        elif utils.check_bars_price_fixed(bars):
            utils.print_trading_log(
                "<{}> price is fixed during last 3 candles.".format(ticker['symbol']))
            exit_trading = True
            exit_note = "Price fixed during last 3 candles."
        return (exit_trading, exit_note)

    def trade(self, ticker, m1_bars=pd.DataFrame()):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit=50)
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
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
            m2_bars = utils.convert_2m_bars(m1_bars)
            if m2_bars.empty:
                return

            if not utils.check_bars_updated(m1_bars):
                utils.print_trading_log(
                    "<{}> candle chart is not updated, stop trading!".format(symbol))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            # if not utils.check_bars_volatility(m1_bars):
            #     utils.print_trading_log("<{}> candle chart is not volatility, stop trading!".format(symbol))
            #     # remove from monitor
            #     del tracking_tickers[symbol]
            #     return

            # check if last sell time is too short compare current time
            # if ticker['last_sell_time'] != None and (datetime.now() - ticker['last_sell_time']) < timedelta(seconds=TRADE_INTERVAL):
            #     utils.print_trading_log("Don't buy <{}> too quick after sold!".format(symbol))
            #     return

            # calculate and fill ema 9 data
            m2_bars['ema9'] = m2_bars['close'].ewm(span=9, adjust=False).mean()
            current_candle = m2_bars.iloc[-1]
            prev_candle = m2_bars.iloc[-2]

            # check entry: current price above vwap and ema 9, entry if first candle make new high
            if self.check_entry(ticker, m2_bars):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                ask_price = webullsdk.get_ask_price_from_quote(quote)
                # bid_price = webullsdk.get_bid_price_from_quote(quote)
                if ask_price == None:
                    return
                # gap = (ask_price - bid_price) / bid_price
                # if gap > config.MAX_BID_ASK_GAP_RATIO:
                #     utils.print_trading_log("<{}>[{}] gap too large, ask: {}, bid: {}, stop trading!".format(
                #         symbol, ticker_id, ask_price, bid_price))
                #     # remove from monitor
                #     del self.tracking_tickers[symbol]
                #     return
                usable_cash = webullsdk.get_usable_cash()
                buy_position_amount = self.get_buy_order_limit(ticker)
                if usable_cash <= buy_position_amount:
                    utils.print_trading_log(
                        "Not enough cash to buy <{}>, ask price: {}!".format(symbol, ask_price))
                    return
                buy_quant = (int)(buy_position_amount / ask_price)
                if buy_quant > 0:
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    utils.print_trading_log("Trading <{}>, price: {}, vwap: {}, ema9: {}, volume: {}".format(
                        symbol, current_candle['close'], current_candle['vwap'], round(current_candle['ema9'], 3), int(current_candle['volume'])))
                    utils.print_trading_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                        symbol, buy_quant, ask_price))
                    # update pending buy
                    self.update_pending_buy_order(
                        ticker, order_response, stop_loss=prev_candle['low'])
                else:
                    utils.print_trading_log(
                        "Order amount limit not enough for <{}>, price: {}".format(symbol, ask_price))
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                utils.print_trading_log(
                    "Finding <{}> position error!".format(symbol))
                return
            # cost = float(ticker_position['cost'])
            # last_price = float(ticker_position['lastPrice'])
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate
            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = self.tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                self.tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate
            # quantity = int(ticker_position['position'])
            # utils.print_trading_log("Checking <{}>, cost: {}, last: {}, change: {}%".format(
            #     symbol, cost, last_price, round(profit_loss_rate * 100, 2)))

            # cancel buy prev low stop loss if hit 1% profit
            if profit_loss_rate >= 0.01:
                self.tracking_tickers[symbol]['stop_loss'] = None

            last_price = float(ticker_position['lastPrice'])
            cost_price = float(ticker_position['costPrice'])

            # check stop loss
            exit_trading, exit_note = self.check_stop_loss(
                ticker, ticker_position)

            # sell if drawdown 1% from max P&L rate
            # if max_profit_loss_rate - profit_loss_rate >= 0.01:
            #     exit_trading = True

            # check if holding too long without profit
            if not exit_trading and (datetime.now() - ticker['order_filled_time']) >= timedelta(seconds=config.HOLDING_ORDER_TIMEOUT_IN_SEC) and profit_loss_rate < 0.01:
                utils.print_trading_log(
                    "Holding <{}> too long!".format(symbol))
                exit_note = "Holding too long!"
                exit_trading = True

            if not exit_trading:
                # get 2m bar charts
                m2_bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=20))

                # get bars error
                if m2_bars.empty:
                    utils.print_trading_log(
                        "<{}> bars data error!".format(symbol))
                    exit_note = "Bars data error!"
                    exit_trading = True
                else:
                    # check exit trade
                    exit_trading, exit_note = self.check_exit(ticker, m2_bars)

            # exit trading
            if exit_trading:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = webullsdk.get_bid_price_from_quote(quote)
                if bid_price == None:
                    return
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=holding_quantity)
                utils.print_trading_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                utils.print_trading_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    symbol, order_response, exit_note=exit_note)
                # update trading stats
                self.update_trading_stats(
                    ticker, last_price, cost_price, profit_loss_rate)

    def check_if_trade_price_new_high(self, ticker, price):
        return True

    def check_if_track_ticker(self, ticker):
        # # check if sell not long ago
        # if symbol in self.tracking_stats and (datetime.now() - self.tracking_stats[symbol]['last_trade_time']) <= timedelta(seconds=100):
        #     return False
        return True

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
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            ticker_id = gainer["ticker_id"]
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            # utils.print_trading_log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= config.MIN_SURGE_CHANGE_RATIO and self.check_if_track_ticker(ticker):
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
                m2_bars = utils.convert_2m_bars(m1_bars)
                if m2_bars.empty:
                    continue
                # use latest 2 candle
                latest_candle = m2_bars.iloc[-1]
                latest_candle2 = m2_bars.iloc[-2]
                # check if trasaction amount meets requirement
                if self.check_track(latest_candle) or self.check_track(latest_candle2):
                    # found trading ticker
                    self.tracking_tickers[symbol] = ticker
                    utils.print_trading_log(
                        "Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)

    def on_end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

        # save trading logs
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())
