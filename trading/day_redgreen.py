# -*- coding: utf-8 -*-

from datetime import datetime, date
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser
from sdk import webullsdk
from scripts import utils, config


# Red to green day trading class

class DayTradingRedGreen(StrategyBase):

    def get_tag(self):
        return "DayTradingRedGreen"

    def get_setup(self):
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        prev_day_close = ticker['prev_close']
        prev_day_high = ticker['prev_high']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(
                ticker, stop_tracking=False, resubmit_count=50)
            return

        holding_quantity = ticker['positions']

        # fetch 1m bar charts
        m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
        m2_bars = utils.convert_2m_bars(m1_bars)
        if m2_bars.empty:
            return

        current_candle = m2_bars.iloc[-1]
        prev_candle = m2_bars.iloc[-2]

        # current price data
        current_close = current_candle['close']
        current_high = current_candle['high']
        current_low = current_candle['low']
        prev_low = prev_candle['low']
        current_volume = int(current_candle['volume'])

        if holding_quantity == 0:

            if not utils.check_bars_updated(m2_bars):
                utils.print_trading_log(
                    "<{}> candle chart is not updated, stop trading!".format(symbol))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            if not utils.check_bars_has_volume(m2_bars, time_scale=2):
                utils.print_trading_log(
                    "<{}> candle chart has not enough volume, stop trading!".format(symbol))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            if not utils.check_bars_rel_volume(m2_bars):
                utils.print_trading_log(
                    "<{}> candle chart has no relative volume, stop trading!".format(symbol))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            now = datetime.now()

            # check entry, current price above prev day close with (prev price below or not long after market open)
            if current_low >= prev_day_close and (prev_low <= prev_day_close or (now - datetime(now.year, now.month, now.day, 9, 30)).seconds <= 300):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                ask_price = webullsdk.get_ask_price_from_quote(quote)
                if ask_price == None:
                    return
                # check if ask_price is too high above prev day close
                if (ask_price - prev_day_close) / prev_day_close > config.MAX_PREV_DAY_CLOSE_GAP_RATIO:
                    utils.print_trading_log("<{}> gap too large, ask: {}, prev day close: {}, stop trading!".format(
                        symbol, ask_price, prev_day_close))
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
                    utils.print_trading_log("Trading <{}>, price: {}, volume: {}".format(
                        symbol, current_close, current_volume))
                    utils.print_trading_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                        symbol, buy_quant, ask_price))
                    # update pending buy
                    self.update_pending_buy_order(
                        ticker, order_response, stop_loss=prev_day_close)
                else:
                    utils.print_trading_log(
                        "Order amount limit not enough for <{}>, price: {}".format(symbol, ask_price))
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                utils.print_trading_log(
                    "Finding <{}> position error!".format(symbol))
                return
            # profit loss rate
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate
            # check if exit trading
            exit_trading = False
            last_price = float(ticker_position['lastPrice'])
            # check stop loss, prev day close
            if current_high < ticker['stop_loss']:
                exit_note = "Stop loss at {}!".format(last_price)
                exit_trading = True
            # check taking profit, current price above prev day high
            if last_price >= prev_day_high:
                exit_note = "Take profit at {}!".format(last_price)
                exit_trading = True
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
                utils.print_trading_log("📈 Exit trading <{}> P&L: {}%".format(
                    symbol, round(profit_loss_rate * 100, 2)))
                utils.print_trading_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    ticker, order_response, exit_note=exit_note)

    def on_begin(self):

        if not self.is_regular_market_hour():
            return

        # default today
        last_market_day = datetime.today().date()
        first_gainer = HistoricalTopGainer.objects.last()
        if first_gainer:
            last_market_day = first_gainer.date

        # hist top gainers
        top_gainers = HistoricalTopGainer.objects.filter(date=last_market_day)
        # update tracking_tickers
        for gainer in top_gainers:
            quote = webullsdk.get_quote(ticker_id=gainer.ticker_id)
            if 'open' in quote:
                # weak open
                if float(quote['open']) <= gainer.price:
                    key_stat = utils.get_hist_key_stat(
                        gainer.symbol, last_market_day)
                    ticker = self.build_tracking_ticker(
                        gainer.symbol, gainer.ticker_id, prev_close=gainer.price, prev_high=key_stat.high)
                    self.tracking_tickers[gainer.symbol] = ticker
                    utils.print_trading_log(
                        "Add gainer <{}> to trade!".format(gainer.symbol))
            else:
                utils.print_trading_log(
                    "Cannot find <{}> open price!".format(gainer.symbol))
        # hist top losers
        top_losers = HistoricalTopLoser.objects.filter(date=last_market_day)
        # update tracking_tickers
        for loser in top_losers:
            quote = webullsdk.get_quote(ticker_id=loser.ticker_id)
            if 'open' in quote:
                # weak open
                if float(quote['open']) <= loser.price:
                    key_stat = utils.get_hist_key_stat(
                        loser.symbol, last_market_day)
                    ticker = self.build_tracking_ticker(
                        loser.symbol, loser.ticker_id, prev_close=loser.price, prev_high=key_stat.high)
                    self.tracking_tickers[loser.symbol] = ticker
                    utils.print_trading_log(
                        "Add loser <{}> to trade!".format(loser.symbol))
            else:
                utils.print_trading_log(
                    "Cannot find <{}> open price!".format(loser.symbol))

    def is_power_hour(self):
        now = datetime.now()
        if now.hour <= 12:
            return True
        return False

    def on_update(self):
        if not self.is_regular_market_hour():
            self.trading_end = False
            return

        # only trade regular market hour before 13:00
        if self.is_power_hour():
            # trading tickers
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                # do trade
                self.trade(ticker)
        else:
            self.trading_end = True

    def on_end(self):
        # check if still holding any positions before exit
        self.clear_positions()

        # save trading logs
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())
