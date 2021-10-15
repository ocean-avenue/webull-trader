# -*- coding: utf-8 -*-

from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from webull_trader.models import EarningCalendar
from sdk import webullsdk
from scripts import utils, config


# Breakout day trading class

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
            utils.print_trading_log(
                "<{}> price is not above vwap, no entry!".format(symbol))
            return False
        period_bars = bars.head(len(bars) - 1).tail(self.entry_period)
        period_high_price = 0
        period_low_price = 9999
        for _, row in period_bars.iterrows():
            # use close price for period high
            if row['close'] > period_high_price:
                period_high_price = row['close']
            # use low price for period low
            if row['low'] < period_low_price:
                period_low_price = row['low']
        # check if new high
        if current_price <= period_high_price:
            utils.print_trading_log(
                "<{}> price (${}) is not breakout high (${}), no entry!".format(symbol, current_price, period_high_price))
            return False
            return False
        if not self.check_if_trade_price_new_high(ticker, current_price):
            return False

        # check ema 9
        if current_price < current_candle['ema9']:
            utils.print_trading_log(
                "<{}> price is not above ema9, no entry!".format(symbol))
            return False

        # check if current low is above period low price
        current_low = current_candle['low']
        if current_low < period_low_price:
            utils.print_trading_log(
                "<{}> current low (${}) is lower than period low (${}), no entry!".format(symbol, current_low, period_low_price))
            return False

        # # check if gap already too large
        # if period_high_price * config.PERIOD_HIGH_PRICE_GAP_RATIO < current_price:
        #     utils.print_trading_log("<{}> new high price gap too large, new high: {}, period high: {}, no entry!".format(
        #         ticker['symbol'], current_price, period_high_price))
        #     return False

        # # check if current candle already surge too much
        # if (current_price - prev_close) / prev_close >= config.MAX_DAY_ENTRY_CANDLE_SURGE_RATIO:
        #     surge_ratio = "{}%".format(round((current_price - prev_close) / prev_close * 100, 2))
        #     utils.print_trading_log(
        #         "<{}> current price (${}) already surge {} than prev close (${}), no entry!".format(symbol, current_price, surge_ratio, prev_close))
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

        if self.is_regular_market_hour() and not utils.check_bars_has_amount(bars, time_scale=self.time_scale, period=5) and \
                not utils.check_bars_has_volume(bars, time_scale=self.time_scale, period=5) and not utils.check_bars_rel_volume(bars) and \
                not utils.check_bars_amount_grinding(bars, period=5):
            # has no relative volume
            utils.print_trading_log(
                "<{}> candle chart volume not meet requirements, no entry!".format(symbol))
            return False

        if self.is_regular_market_hour() and not utils.check_bars_volatility(bars):
            # no volatility
            utils.print_trading_log(
                "<{}> candle chart is not volatility, no entry!".format(symbol))
            return False

        if utils.check_bars_has_long_wick_up(bars, period=self.entry_period):
            # has long wick up
            utils.print_trading_log(
                "<{}> candle chart has long wick up, no entry!".format(symbol))
            return False

        if not (utils.check_bars_has_largest_green_candle(bars) and utils.check_bars_has_more_green_candle(bars)) and \
                not utils.check_bars_has_most_green_candle(bars):
            # not most green candles and no largest green candle
            utils.print_trading_log(
                "<{}> candle chart has no most green candles or largest candle is red, no entry!".format(symbol))
            return False

        if utils.check_bars_has_bearish_candle(bars, period=5):
            # has bearish candle
            utils.print_trading_log(
                "<{}> candle chart has bearish candle, no entry!".format(symbol))
            return False

        ROC = self.get_price_rate_of_change(bars, period=self.entry_period)
        if ROC <= config.DAY_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            utils.print_trading_log(
                "<{}> candle chart price rate of change for {} period ({}) is weak, no entry!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        if symbol in self.tracking_stats:
            last_trade_time = self.tracking_stats[symbol]['last_trade_time']
            if last_trade_time and (datetime.now() - last_trade_time) <= timedelta(seconds=config.TRADE_INTERVAL_IN_SEC * self.time_scale):
                utils.print_trading_log(
                    "<{}> try buy too soon after last sell, no entry!".format(symbol))
                return False

        return True

    def check_exit(self, ticker, bars):
        symbol = ticker['symbol']
        exit_period = ticker['exit_period'] or self.exit_period
        # latest candle
        current_candle = bars.iloc[-1]
        current_candle_time = bars.index[-1].to_pydatetime()
        last_buy_time = ticker['last_buy_time']
        # align timezone info
        last_buy_time = last_buy_time.replace(
            tzinfo=current_candle_time.tzinfo)
        # make sure last formed candle is not same as buy candle
        if last_buy_time > current_candle_time:
            if ((last_buy_time - current_candle_time).seconds//60) % 60 == 0:
                return (False, None)
        else:
            if ((current_candle_time - last_buy_time).seconds//60) % 60 == 0:
                return (False, None)
        exit_trading = False
        exit_note = None
        current_price = current_candle['close']
        period_bars = bars.head(len(bars) - 1).tail(exit_period)
        period_low_price = 99999
        period_low_idx = -1
        for i in range(0, len(period_bars)):
            close_price = period_bars.iloc[i].close
            if close_price < period_low_price:
                period_low_price = close_price
                period_low_idx = i
        if period_low_idx < len(period_bars) - 1:
            # add 1% threshold
            threshold = 0.01
            period_low_price = period_low_price * (1-threshold)
        # check if new low
        if current_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(exit_period)
            utils.print_trading_log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, current_price, round(period_low_price, 2)))
        # # check if has long wick up
        # elif utils.check_bars_has_long_wick_up(bars, period=4):
        #     utils.print_trading_log(
        #         "<{}> candle chart has long wick up, exit!".format(symbol))
        #     exit_trading = True
        #     exit_note = "Candle chart has long wick up."
        # check if bar chart has volatility
        elif self.is_extended_market_hour() and not utils.check_bars_volatility(bars):
            utils.print_trading_log(
                "<{}> candle chart is not volatility, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is not volatility."
        # check if bar chart is at peak
        elif self.is_regular_market_hour() and utils.check_bars_at_peak(bars):
            utils.print_trading_log(
                "<{}> candle chart is at peak, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart is at peak."
        elif utils.check_bars_reversal(bars):
            utils.print_trading_log(
                "<{}> candle chart will reversal, exit!".format(symbol))
            exit_trading = True
            exit_note = "Candle chart will reversal."
        elif self.check_if_trade_period_timeout(ticker):
            utils.print_trading_log(
                "<{}> trading period timeout, exit!".format(symbol))
            exit_trading = True
            exit_note = "Trading period timeout."

        return (exit_trading, exit_note)

    def check_scale_in(self, ticker, bars, position):
        return False

    def check_stop_profit(self, ticker, position):
        exit_trading = False
        exit_note = None
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        if profit_loss_rate >= 1:
            exit_trading = True
            exit_note = "Home run at {}!".format(position['lastPrice'])
        return (exit_trading, exit_note)

    def check_stop_loss(self, ticker, position):
        exit_trading = False
        exit_note = None
        last_price = float(position['lastPrice'])
        # check stop loss
        if ticker['stop_loss'] and last_price < ticker['stop_loss']:
            exit_trading = True
            exit_note = "Stop loss at {}!".format(last_price)
        return (exit_trading, exit_note)

    def check_if_trade_price_new_high(self, ticker, price):
        return True

    def check_if_trade_period_timeout(self, ticker):
        return False

    def get_stop_loss_price(self, buy_price, bars):
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        # use max( min( prev candle middle, buy price -2% ), buy price -5% )
        # return max(
        #     min(round((prev_candle['high'] + prev_candle['low']) / 2, 2),
        #         round(buy_price * (1 - config.MIN_DAY_STOP_LOSS), 2)),
        #     round(buy_price * (1 - config.MAX_DAY_STOP_LOSS), 2))
        return min(current_candle['low'], prev_candle['low'])

    def get_scale_stop_loss_price(self, buy_price, bars):
        return None

    def get_price_rate_of_change(self, bars, period=10):
        period = min(len(bars) - 1, period)
        period_bars = bars.tail(period + 1)
        period_bars = period_bars.head(period)
        period_price = period_bars.iloc[0]['close']
        current_price = bars.iloc[-1]['close']
        ROC = (current_price - period_price) / period_price * 100
        return ROC

    def update_exit_period(self, ticker, position):
        return

    def submit_buy_order(self, ticker, bars, scale_in=False):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        usable_cash = webullsdk.get_usable_cash()
        utils.save_webull_min_usable_cash(usable_cash)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            utils.print_trading_log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        # buy_price = self.get_buy_price(ticker)
        buy_price = self.get_buy_price2(ticker)
        if buy_price == None:
            return
        # candle data
        current_candle = bars.iloc[-1]
        buy_quant = (int)(buy_position_amount / buy_price)
        # reset exit period
        self.tracking_tickers[symbol]['exit_period'] = self.exit_period
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
            if scale_in:
                stop_loss = self.get_scale_stop_loss_price(buy_price, bars)
            else:
                stop_loss = self.get_stop_loss_price(buy_price, bars)
            # update pending buy
            self.update_pending_buy_order(
                ticker, order_response, stop_loss=stop_loss)
        else:
            utils.print_trading_log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

    def submit_sell_order(self, ticker, position, note):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        holding_quantity = ticker['positions']
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        sell_price = self.get_sell_price(ticker)
        # sell_price = self.get_sell_price2(position)
        last_price = float(position['lastPrice'])
        cost_price = float(position['costPrice'])
        if sell_price == None:
            sell_price = last_price
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
            ticker, order_response, exit_note=note)
        # update trading stats
        self.update_trading_stats(
            ticker, last_price, cost_price, profit_loss_rate)

    def trade(self, ticker, m1_bars=pd.DataFrame()):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            target_units = config.DAY_TARGET_UNITS
            # reduce size in low volume market hour
            if self.is_extended_market_hour():
                target_units = config.DAY_EXTENDED_TARGET_UNITS
            self.check_buy_order_filled(ticker, target_units=target_units)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit_count=50)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0:
            timeout = False
            if ticker['last_buy_time'] and (datetime.now() - ticker['last_buy_time']) >= timedelta(seconds=config.OBSERVE_TIMEOUT_IN_SEC):
                timeout = True
            elif (datetime.now() - ticker['start_time']) >= timedelta(seconds=config.OBSERVE_TIMEOUT_IN_SEC):
                timeout = True
            if timeout:
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

            # check entry: current price above vwap, entry period minutes new high
            if self.check_entry(ticker, bars):
                self.submit_buy_order(ticker, bars, scale_in=False)
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
            # update exit period by profit loss rate
            self.update_exit_period(ticker, ticker_position)

            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = self.tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                self.tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate

            # check stop profit, home run
            exit_trading, exit_note = self.check_stop_profit(
                ticker, ticker_position)
            if not exit_trading:
                # get 1m bar charts
                # check_bars_at_peak require 30 bars
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.exit_period*self.time_scale + 30))
                # check bars error
                if m1_bars.empty:
                    utils.print_trading_log(
                        "<{}> bars data error!".format(symbol))
                    exit_trading = True
                    exit_note = "Bars data error!"
            if not exit_trading:
                # convert bars
                bars = m1_bars
                if self.time_scale == 5:
                    bars = utils.convert_5m_bars(m1_bars)
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(
                    ticker, ticker_position)
            if not exit_trading:
                utils.print_trading_log("Checking exit for <{}>, unrealized P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                # check exit trade
                exit_trading, exit_note = self.check_exit(ticker, bars)

            # exit trading
            if exit_trading:
                self.submit_sell_order(ticker, ticker_position, exit_note)
            # check scale in position
            elif self.check_scale_in(ticker, bars, ticker_position):
                # check scale in position
                self.submit_buy_order(ticker, bars, scale_in=True)

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
            # check if can trade with requirements, skip check top 1 gainer
            if not self.check_can_trade_ticker(ticker):
                # utils.print_trading_log(
                #     "Can not trade <{}>, skip...".format(symbol))
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


# Breakout day trading class, using ask price for entry

class DayTradingBreakoutAsk(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutAsk"

    def get_buy_price(self, ticker):
        ticker_id = ticker['ticker_id']
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        return ask_price

    def get_buy_price2(self, ticker):
        ticker_id = ticker['ticker_id']
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        return ask_price


# Breakout day trade, adjust exit period by profit & loss rate.

class DayTradingBreakoutDynExit(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutDynExit"

    def update_exit_period(self, ticker, position):
        symbol = ticker['symbol']
        profit_loss_rate = float(position['unrealizedProfitLossRate'])
        current_exit_period = ticker['exit_period'] or 1
        # if profit_loss_rate >= 0.9 and current_exit_period > 1:
        #     self.tracking_tickers[symbol]['exit_period'] = 1
        # elif profit_loss_rate >= 0.7 and current_exit_period > 3:
        #     self.tracking_tickers[symbol]['exit_period'] = 3
        if profit_loss_rate >= 0.5 and current_exit_period > 5:
            self.tracking_tickers[symbol]['exit_period'] = 5
        elif profit_loss_rate >= 0.3 and current_exit_period > 7:
            self.tracking_tickers[symbol]['exit_period'] = 7


# Breakout day trading class, will check earning stock during earning date

class DayTradingBreakoutEarnings(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutEarnings"

    def get_setup(self):
        if len(self.earning_tickers) == 0:
            if self.entry_period == 30:
                return SetupType.DAY_30_CANDLES_NEW_HIGH
            elif self.entry_period == 20:
                return SetupType.DAY_20_CANDLES_NEW_HIGH
            return SetupType.DAY_10_CANDLES_NEW_HIGH
        else:
            return SetupType.DAY_EARNINGS_GAP

    def check_trade(self, symbol, ticker_id, change_percentage):
        ticker = self.build_tracking_ticker(symbol, ticker_id)
        # check if can trade with requirements
        if not self.check_can_trade_ticker(ticker):
            return
        # check gap change
        if change_percentage >= config.MIN_SURGE_CHANGE_RATIO:
            if self.is_extended_market_hour():
                m1_bars = webullsdk.get_1m_bars(
                    ticker_id, count=(self.entry_period+5))
                if m1_bars.empty:
                    return
                # use latest 2 candle
                latest_candle = m1_bars.iloc[-1]
                latest_candle2 = m1_bars.iloc[-2]
                # check if trasaction amount and volume meets requirement
                if self.check_surge(ticker, latest_candle) or self.check_surge(ticker, latest_candle2):
                    # found trading ticker
                    self.tracking_tickers[symbol] = ticker
                    utils.print_trading_log(
                        "Found <{}> to trade!".format(symbol))
                    # do trade
                    self.trade(ticker, m1_bars=m1_bars)
            elif self.is_regular_market_hour():
                # found trading ticker
                self.tracking_tickers[symbol] = ticker
                utils.print_trading_log("Found <{}> to trade!".format(symbol))
                # do trade
                self.trade(ticker)

    def on_begin(self):
        self.earning_tickers = []
        # check earning calendars
        today = date.today()
        if self.is_pre_market_hour() or self.is_regular_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="bmo")
        elif self.is_after_market_hour():
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time="amc")
        # update earning_tickers
        for earning in earnings:
            symbol = earning.symbol
            ticker_id = webullsdk.get_ticker(symbol=symbol)
            self.earning_tickers.append({
                "symbol": symbol,
                "ticker_id": ticker_id,
            })
            utils.print_trading_log(
                "Add ticker <{}> to check earning gap!".format(symbol))

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        # no earning symbol found
        if len(self.earning_tickers) == 0:
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
                # utils.print_trading_log("Scanning <{}>...".format(symbol))
                change_percentage = gainer["change_percentage"]
                self.check_trade(symbol, ticker_id, change_percentage)
        else:
            for earning_ticker in self.earning_tickers:
                symbol = earning_ticker["symbol"]
                ticker_id = earning_ticker["ticker_id"]
                # check if ticker already in monitor
                if symbol in self.tracking_tickers:
                    continue
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    continue
                change_percentage = 0.0
                if self.is_extended_market_hour():
                    if 'pChRatio' in quote:
                        change_percentage = float(quote['pChRatio'])
                elif self.is_regular_market_hour():
                    if 'changeRatio' in quote:
                        change_percentage = float(quote['changeRatio'])
                self.check_trade(symbol, ticker_id, change_percentage)


# Breakout day trade, no entry if the price not break max of last high price.

class DayTradingBreakoutNewHigh(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutNewHigh"

    def check_if_trade_price_new_high(self, ticker, price):
        symbol = ticker['symbol']
        if symbol in self.tracking_stats and self.tracking_stats[symbol]['last_high_price'] != None:
            last_high_price = self.tracking_stats[symbol]['last_high_price']
            return price > last_high_price
        return True


# Breakout day trade, exit if trading period timeout.

class DayTradingBreakoutPeriod(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutPeriod"

    def check_if_trade_period_timeout(self, ticker):
        if (datetime.now() - ticker['last_buy_time']) >= timedelta(seconds=config.DAY_PERIOD_TIMEOUT_IN_SEC):
            return True
        return False


# Breakout day trade, find pre-market losers and aim for reversal.

class DayTradingBreakoutPreLosers(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutPreLosers"

    def on_begin(self):
        self.preloser_tickers = []
        # check pre-market losers
        if self.is_regular_market_hour():
            self.preloser_tickers = webullsdk.get_pre_market_losers(count=10)
            utils.print_trading_log("Add {} tickers to check loser reversal!".format(
                len(self.preloser_tickers)))

    def on_update(self):

        if self.is_pre_market_hour() or self.is_after_market_hour():
            # only trade in regular hour
            return

        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        for preloser_ticker in self.preloser_tickers:
            symbol = preloser_ticker["symbol"]
            ticker_id = preloser_ticker["ticker_id"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            # found trading ticker
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            self.tracking_tickers[symbol] = ticker
            utils.print_trading_log("Found <{}> to trade!".format(symbol))
            # do trade
            self.trade(ticker)


# Breakout day trading class, scale if reach add unit price

class DayTradingBreakoutScale(DayTradingBreakout):

    def get_tag(self):
        return "DayTradingBreakoutScale"

    def check_scale_in(self, ticker, bars, position):
        symbol = ticker['symbol']
        last_candle = bars.iloc[-2]
        last_price = last_candle['close']
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
        period_bars = bars.head(len(bars) - 2).tail(self.entry_period)
        period_high_price = 0
        for _, row in period_bars.iterrows():
            close_price = row['close']  # use close price
            if close_price > period_high_price:
                period_high_price = close_price
        # check if new high
        if last_price < period_high_price:
            return False

        if self.is_regular_market_hour() and not utils.check_bars_updated(bars):
            utils.print_trading_log(
                "<{}> candle chart is not updated, stop scale in!".format(symbol))
            return False

        if self.is_regular_market_hour() and not utils.check_bars_continue(bars, time_scale=self.time_scale):
            utils.print_trading_log(
                "<{}> candle chart is not continue, stop scale in!".format(symbol))
            return False

        if self.is_regular_market_hour() and not utils.check_bars_has_amount(bars, time_scale=self.time_scale, period=5) and \
                not utils.check_bars_has_volume(bars, time_scale=self.time_scale, period=5) and not utils.check_bars_rel_volume(bars) and \
                not utils.check_bars_amount_grinding(bars, period=5) and not utils.check_bars_all_green(bars, period=5):
            # has no volume and amount
            utils.print_trading_log(
                "<{}> candle chart volume not meet requirements, no scale in!".format(symbol))
            return False

        ROC = self.get_price_rate_of_change(bars, period=self.entry_period)
        if ROC <= config.DAY_SCALE_PRICE_RATE_OF_CHANGE:
            # price rate of change is weak
            utils.print_trading_log(
                "<{}> candle chart price rate of change for {} period ({}) is weak, no scale in!".format(symbol, self.entry_period, round(ROC, 2)))
            return False

        utils.print_trading_log("Scale in <{}> position".format(symbol))
        return True

    def get_scale_stop_loss_price(self, buy_price, bars):
        current_candle = bars.iloc[-1]
        prev_candle = bars.iloc[-2]
        return min(current_candle['low'], prev_candle['low'])

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
