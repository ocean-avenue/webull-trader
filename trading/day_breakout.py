# -*- coding: utf-8 -*-

# Breakout day trading class

from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


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
        if close * volume >= self.min_surge_amount and volume >= self.min_surge_volume and close >= vwap:
            self.print_log("Found <{}> to trade!".format(ticker["symbol"]))
            return True
        return False

    def check_entry(self, ticker, bars):
        symbol = ticker["symbol"]
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
        if not self.check_if_trade_price_new_high(symbol, current_price):
            return False
        # check ema 9
        if current_price < current_candle['ema9']:
            self.print_log(
                "<{}> price is not above ema9, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False
        # check if gap already too large
        if period_high_price * 1.1 < current_price:
            self.print_log("<{}> new high price gap too large, new high: {}, period high: {}, no entry!".format(
                ticker['symbol'], current_price, period_high_price))
            return False
        if self.is_regular_market_hour() and not utils.check_bars_updated(bars):
            self.print_log(
                "<{}> candle chart is not updated, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if self.is_regular_market_hour() and not utils.check_bars_continue(bars, time_scale=self.time_scale):
            self.print_log(
                "<{}> candle chart is not continue, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if self.is_regular_market_hour() and not utils.check_bars_has_amount(bars, time_scale=self.time_scale, period=5) and not utils.check_bars_rel_volume(bars):
            # has no volume and no relative volume
            self.print_log(
                "<{}> candle chart has not enough volume, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        # if utils.check_bars_has_long_wick_up(bars):
        #     # has long wick up
        #     self.print_log(
        #         "<{}> candle chart has long wick up, stop trading!".format(symbol))
        #     # remove from monitor
        #     del self.tracking_tickers[symbol]
        #     return False
        # TODO, for trading log
        period = 10
        long_wick_up_count = 0
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        for _, row in period_bars.iterrows():
            mid = max(row["close"], row["open"])
            high = row["high"]
            low = row["low"]
            if (mid - low) > 0 and (high - mid) / (mid - low) >= 2:
                self.print_log("Found long wick up, open: {}, close: {}, low: {}, high: {}!".format(
                    row["open"],
                    row["close"],
                    row["low"],
                    row["high"],
                ))
                long_wick_up_count += 1
        if long_wick_up_count >= 1:
            self.print_log(
                "<{}> candle chart has long wick up, stop trading!".format(symbol))
            # TODO, remove
            self.trading_logs.append("bars:")
            self.trading_logs.append(str(bars))
            self.trading_logs.append("period_bars:")
            self.trading_logs.append(str(period_bars))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if not utils.check_bars_volatility(bars):
            self.print_log(
                "<{}> candle chart is not volatility, stop trading!".format(symbol))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return False

        if symbol in self.tracking_stats:
            last_trade_time = self.tracking_stats[symbol]['last_trade_time']
            if last_trade_time and (datetime.now() - last_trade_time) <= timedelta(seconds=60 * self.time_scale):
                self.print_log(
                    "<{}> try buy too soon after last sell, stop trading!".format(symbol))
                # remove from monitor
                del self.tracking_tickers[symbol]
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
        symbol = ticker['symbol']
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
            self.print_log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, current_price, period_low_price))
        # # check if has long wick up
        # elif utils.check_bars_has_long_wick_up(bars):
        #     self.print_log(
        #         "<{}> candle chart has long wick up, exit!".format(symbol))
        #     exit_trading = True
        #     exit_note = "Candle chart has long wick up."
        # check if bar chart has volatility
        elif not utils.check_bars_volatility(bars):
            self.print_log(
                "<{}> candle chart is not volatility, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is not volatility."

        if not exit_trading:
            # TODO, for trading log
            period = 5
            long_wick_up_count = 0
            period_bars = bars.tail(period + 1)
            period_bars = period_bars.head(period)
            for _, row in period_bars.iterrows():
                mid = max(row["close"], row["open"])
                high = row["high"]
                low = row["low"]
                if (mid - low) > 0 and (high - mid) / (mid - low) >= 2:
                    self.print_log("Found long wick up, open: {}, close: {}, low: {}, high: {}!".format(
                        row["open"],
                        row["close"],
                        row["low"],
                        row["high"],
                    ))
                    long_wick_up_count += 1
            if long_wick_up_count >= 1:
                self.print_log(
                    "<{}> candle chart has long wick up, exit!".format(symbol))
                # TODO, remove
                self.trading_logs.append("bars:")
                self.trading_logs.append(str(bars))
                self.trading_logs.append("period_bars:")
                self.trading_logs.append(str(period_bars))
                exit_trading = True
                exit_note = "Candle chart has long wick up."

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
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(seconds=self.observe_timeout_in_sec):
            self.print_log("Trading <{}> session timeout!".format(symbol))
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
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                # bid_price = webullsdk.get_bid_price_from_quote(quote)
                ask_price = webullsdk.get_ask_price_from_quote(quote)
                if ask_price == None:
                    return
                usable_cash = webullsdk.get_usable_cash()
                buy_position_amount = self.get_buy_order_limit(symbol)
                if usable_cash <= buy_position_amount:
                    self.print_log(
                        "Not enough cash to buy <{}>, ask price: {}!".format(symbol, ask_price))
                    return
                buy_quant = (int)(buy_position_amount / ask_price)
                if buy_quant > 0:
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    self.print_log("Trading <{}>, price: {}, vwap: {}, volume: {}".format(
                        symbol, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                    self.print_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                        symbol, buy_quant, ask_price))
                    # update pending buy
                    self.update_pending_buy_order(
                        symbol, order_response, stop_loss=prev_candle['low'])
                else:
                    self.print_log(
                        "Order amount limit not enough for <{}>, price: {}".format(symbol, ask_price))

        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                self.print_log("Finding <{}> position error!".format(symbol))
                return
            if holding_quantity <= 0:
                # position is negitive, some unknown error happen
                self.print_log("<{}> holding quantity is negitive {}!".format(
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

            # check stop loss
            exit_trading, exit_note = self.check_stop_loss(
                ticker, ticker_position)

            if not exit_trading:
                # get 1m bar charts
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.exit_period*self.time_scale+5))

                # get bars error
                if m1_bars.empty:
                    self.print_log("<{}> bars data error!".format(symbol))
                    exit_trading = True
                    exit_note = "Bars data error!"
                else:
                    bars = m1_bars
                    if self.time_scale == 5:
                        bars = utils.convert_5m_bars(m1_bars)
                    # check exit trade
                    exit_trading, exit_note = self.check_exit(ticker, bars)

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
                self.print_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                self.print_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, bid_price))
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
        if self.is_regular_market_hour():
            top_gainers = webullsdk.get_top_gainers()
        elif self.is_pre_market_hour():
            top_gainers = webullsdk.get_pre_market_gainers()
        elif self.is_after_market_hour():
            top_gainers = webullsdk.get_after_market_gainers()

        # self.print_log("Scanning top gainers <{}>...".format(
        #     ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
        for gainer in top_gainers:
            symbol = gainer["symbol"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            ticker_id = gainer["ticker_id"]
            # self.print_log("Scanning <{}>...".format(symbol))
            change_percentage = gainer["change_percentage"]
            # check gap change
            if change_percentage >= self.min_surge_change_ratio:
                if self.is_extended_market_hour():
                    m1_bars = webullsdk.get_1m_bars(
                        ticker_id, count=(self.entry_period*self.time_scale+5))
                    if m1_bars.empty:
                        continue
                    # use latest 2 candle
                    latest_candle = m1_bars.iloc[-1]
                    latest_candle2 = m1_bars.iloc[-2]
                    # check if trasaction amount and volume meets requirement
                    ticker = self.get_init_tracking_ticker(symbol, ticker_id)
                    if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                        # found trading ticker
                        self.tracking_tickers[symbol] = ticker
                        # do trade
                        self.trade(ticker, m1_bars=m1_bars)
                elif self.is_regular_market_hour():
                    # found trading ticker
                    ticker = self.get_init_tracking_ticker(symbol, ticker_id)
                    self.tracking_tickers[symbol] = ticker
                    self.print_log("Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.trading_hour, date.today())
