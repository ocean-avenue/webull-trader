# -*- coding: utf-8 -*-

from datetime import date
from trading.strategy.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from scripts import config
from sdk import webullsdk, finvizsdk
from scripts import utils


# VWAP reclaim day trading strategy


# OTOCO order is not available in paper account
class DayTradingVWAPPaper(StrategyBase):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)

    def get_tag(self):
        return "DayTradingVWAP"

    def get_setup(self):
        return SetupType.DAY_VWAP_RECLAIM

    # return (SHOULD_ENTRY, TARGET_PROFIT, STOP_LOSS)
    def check_entry(self, ticker, bars):
        # check if have prev candles below vwap
        below_vwap_count = 0
        period_high = 0
        period_low = config.MAX_SECURITY_PRICE
        for _, candle in bars.iterrows():
            if candle['low'] < candle['vwap']:
                below_vwap_count += 1
            if candle['close'] > period_high:
                period_high = candle['close']
            if candle['low'] < period_low:
                period_low = candle['low']
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        # min stop loss 2%
        period_low = min(round(current_price * 0.98, 2), period_low)
        current_vwap = current_candle['vwap']
        below_vwap_percent = below_vwap_count / len(bars)
        # check if current price above vwap, prev price below vwap and below vwap percentage <= 40%
        if current_price > current_vwap and below_vwap_count > 0 and below_vwap_percent <= 0.4:
            # check if profit/loss ratio is over 2
            if (period_high - current_price) / (current_price - period_low) >= 2.0:
                return (True, period_high, period_low)
        return (False, 0.0, 0.0)

    def check_stop_loss(self, ticker, bars):
        exit_trading = False
        exit_note = None
        stop_loss = ticker['stop_loss']
        for _, candle in bars.iterrows():
            # check if latest low is lower than stop loss
            if candle['low'] < stop_loss:
                exit_trading = True
                exit_note = "Price (${}) below stop loss (${})!".format(
                    candle['low'], stop_loss)
                break
        return (exit_trading, exit_note)

    def check_exit(self, ticker, bars):
        symbol = ticker['symbol']
        exit_trading = False
        exit_note = None
        target_profit = ticker['target_profit']
        for _, candle in bars.iterrows():
            # check if price already reach target profit
            if candle['high'] >= target_profit:
                exit_trading = True
                exit_note = "Price (${}) reach target profit (${}).".format(
                    candle['high'], target_profit)
                utils.print_trading_log("<{}> price (${}) is reach target profit (${}), exit!".format(
                    symbol, candle['high'], target_profit))
                break

        return (exit_trading, exit_note)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit_count=50)
            return

        holding_quantity = ticker['positions']

        if holding_quantity == 0:
            # fetch 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=30)
            if m1_bars.empty:
                return
            bars = m1_bars

            # candle data
            current_candle = bars.iloc[-1]

            should_entry, target_profit, stop_loss = self.check_entry(
                ticker, bars)
            # check entry: current above vwap
            if should_entry:
                # buy_price = self.get_buy_price(ticker)
                buy_price = self.get_buy_price2(ticker)
                if buy_price == None:
                    return
                usable_cash = webullsdk.get_usable_cash()
                utils.save_webull_min_usable_cash(usable_cash)
                buy_position_amount = self.get_buy_order_limit(ticker)
                if usable_cash <= buy_position_amount:
                    utils.print_trading_log(
                        "Not enough cash to buy <{}>, buy price: {}!".format(symbol, buy_price))
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
                    # update pending buy
                    self.update_pending_buy_order(
                        ticker, order_response, target_profit=target_profit, stop_loss=stop_loss)
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

            # get 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=5)

            # get bars error
            if m1_bars.empty:
                utils.print_trading_log("<{}> bars data error!".format(symbol))
                exit_trading = True
                exit_note = "Bars data error!"
            else:

                profit_loss_rate = float(
                    ticker_position['unrealizedProfitLossRate'])
                self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate

                bars = m1_bars
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(ticker, bars)
                # check exit trade
                if not exit_trading:
                    utils.print_trading_log("Checking exit for <{}>, unrealized P&L: {}%".format(
                        symbol, round(profit_loss_rate * 100, 2)))
                    exit_trading, exit_note = self.check_exit(ticker, bars)

                # exit trading
                if exit_trading:
                    # sell_price = self.get_sell_price(ticker)
                    sell_price = self.get_sell_price2(ticker_position)
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
                        ticker, order_response, exit_note=exit_note)
                    # update trading stats
                    self.update_trading_stats(ticker, float(ticker_position['lastPrice']), float(
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
                # utils.print_trading_log(
                #     "Can not trade <{}>, skip...".format(symbol))
                continue
            # add to monitor
            self.tracking_tickers[symbol] = ticker
            # do trade
            self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()


class DayTradingVWAPLargeCap(StrategyBase):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.large_cap_with_major_news = {}

    def get_tag(self):
        return "DayTradingVWAPLargeCap"

    def get_setup(self):
        return SetupType.DAY_VWAP_RECLAIM

    def check_entry(self, ticker, bars):
        # check if have prev candles below vwap
        has_candle_below_vwap = False
        for _, candle in bars.iterrows():
            if candle['close'] < candle['vwap']:
                has_candle_below_vwap = True
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        current_vwap = current_candle['vwap']
        # check if current price above vwap and prev price below vwap
        if current_price > current_vwap and has_candle_below_vwap:
            return True
        return False

    def check_stop_loss(self, ticker, bars):
        exit_trading = False
        exit_note = None
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        current_vwap = current_candle['vwap']
        # check if current price below vwap
        if current_price < current_vwap:
            exit_trading = True
            exit_note = "Stop loss, price ({}) below vwap ({})!".format(
                current_price, current_vwap)
        return (exit_trading, exit_note)

    def check_exit(self, ticker, bars):
        symbol = ticker['symbol']
        exit_trading = False
        exit_note = None
        exit_period = 10
        current_candle = bars.iloc[-1]
        current_price = current_candle['close']
        period_bars = bars.head(len(bars) - 1).tail(exit_period)
        period_low_price = config.MAX_SECURITY_PRICE
        for _, row in period_bars.iterrows():
            close_price = row['close']
            if close_price < period_low_price:
                period_low_price = close_price
        # check if new low
        if current_price < period_low_price:
            exit_trading = True
            exit_note = "{} candles new low.".format(exit_period)
            utils.print_trading_log("<{}> new period low price, new low: {}, period low: {}, exit!".format(
                symbol, current_price, period_low_price))

        return (exit_trading, exit_note)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit_count=50)
            return

        holding_quantity = ticker['positions']

        if holding_quantity == 0:
            # fetch 1m bar charts
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=15)
            if m1_bars.empty:
                return
            bars = m1_bars

            # candle data
            current_candle = bars.iloc[-1]

            # check entry: current above vwap
            if self.check_entry(ticker, bars):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                # bid_price = webullsdk.get_bid_price_from_quote(quote)
                ask_price = webullsdk.get_ask_price_from_quote(quote)
                if ask_price == None:
                    return
                usable_cash = webullsdk.get_usable_cash()
                utils.save_webull_min_usable_cash(usable_cash)
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
                    utils.print_trading_log("Trading <{}>, price: {}, vwap: {}, volume: {}".format(
                        symbol, current_candle['close'], current_candle['vwap'], int(current_candle['volume'])))
                    utils.print_trading_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                        symbol, buy_quant, ask_price))
                    # update pending buy
                    self.update_pending_buy_order(ticker, order_response)
                else:
                    utils.print_trading_log(
                        "Order amount limit not enough for <{}>, price: {}".format(symbol, ask_price))

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
            m1_bars = webullsdk.get_1m_bars(ticker_id, count=15)
            # get bars error
            if m1_bars.empty:
                utils.print_trading_log("<{}> bars data error!".format(symbol))
                exit_trading = True
                exit_note = "Bars data error!"
            else:
                bars = m1_bars
                # check stop loss
                exit_trading, exit_note = self.check_stop_loss(ticker, bars)
                # check exit trade
                if not exit_trading:
                    # check exit trade
                    utils.print_trading_log("Checking exit for <{}>, unrealized P&L: {}%".format(
                        symbol, round(profit_loss_rate * 100, 2)))
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
                utils.print_trading_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                utils.print_trading_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    ticker, order_response, exit_note=exit_note)
                # update trading stats
                self.update_trading_stats(ticker, float(ticker_position['lastPrice']), float(
                    ticker_position['costPrice']), profit_loss_rate)

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # do trade
            self.trade(ticker)

        # find large cap ticker with major news
        large_cap_with_major_news = finvizsdk.fetch_screeners(
            finvizsdk.MAJOR_NEWS_SCREENER)

        for large_cap in large_cap_with_major_news:
            symbol = large_cap["symbol"]
            # already exist in watchlist
            if symbol in self.large_cap_with_major_news:
                continue
            ticker_id = webullsdk.get_ticker(symbol=symbol)
            self.large_cap_with_major_news[symbol] = {
                "symbol": symbol,
                "ticker_id": ticker_id,
            }
            utils.print_trading_log(
                "Found ticker <{}> to check reclaim vwap!".format(symbol))

        for symbol in list(self.large_cap_with_major_news):
            ticker_id = self.large_cap_with_major_news[symbol]["ticker_id"]
            # check if ticker already in monitor
            if symbol in self.tracking_tickers:
                continue
            # init tracking ticker
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            # add to monitor
            self.tracking_tickers[symbol] = ticker
            # do trade
            self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # check if still holding any positions before exit
        self.clear_positions()
