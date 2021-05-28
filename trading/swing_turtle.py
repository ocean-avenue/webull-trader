# -*- coding: utf-8 -*-

# Turtle trading

import time
from datetime import datetime, date, timedelta
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser
from sdk import webullsdk
from scripts import utils


class SwingTurtle(StrategyBase):

    def __init__(self, paper, entry=55, exit=20):
        super().__init__(paper=paper)
        self.entry_period = entry
        self.exit_period = exit

    def get_tag(self):
        return "SwingTurtle"

    def get_setup(self):
        if self.entry_period == 20:
            return SetupType.SWING_20_DAYS_NEW_HIGH
        return SetupType.SWING_55_DAYS_NEW_HIGH

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        prev_day_close = ticker['prev_close']
        prev_day_high = ticker['prev_high']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, stop_tracking=False)
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

            now = datetime.now()

            # check entry, current price above prev day close with (prev price below or not long after market open)
            if current_low >= prev_day_close and (prev_low <= prev_day_close or (now - datetime(now.year, now.month, now.day, 9, 30)).second <= 300):
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None or 'depth' not in quote:
                    return
                ask_price = float(
                    quote['depth']['ntvAggAskList'][0]['price'])
                # check if ask_price is too high above prev day close
                if (ask_price - prev_day_close) / prev_day_close > 0.02:
                    self.print_log("<{}>[{}] gap too large, ask: {}, prev day close: {}, stop trading!".format(
                        symbol, ticker_id, ask_price, prev_day_close))
                    return
                buy_position_amount = self.get_buy_order_limit(symbol)
                buy_quant = (int)(buy_position_amount / ask_price)
                # submit limit order at ask price
                order_response = webullsdk.buy_limit_order(
                    ticker_id=ticker_id,
                    price=ask_price,
                    quant=buy_quant)
                self.print_log("Trading <{}>[{}], price: {}, volume: {}".format(
                    symbol, ticker_id, current_close, current_volume))
                self.print_log("🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                    symbol, ticker_id, buy_quant, ask_price))
                # update pending buy
                self.update_pending_buy_order(
                    symbol, order_response, stop_loss=prev_day_close)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                self.print_log(
                    "Finding <{}>[{}] position error!".format(symbol, ticker_id))
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
                self.print_log("📈 Exit trading <{}>[{}] P&L: {}%".format(
                    symbol, ticker_id, round(profit_loss_rate * 100, 2)))
                self.print_log("🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    symbol, ticker_id, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    symbol, order_response, exit_note=exit_note)

    def check_trading_hour(self):
        valid_time = True
        if datetime.now().hour < 9 or datetime.now().hour >= 16:
            # self.print_log("Skip pre and after market session, quit!")
            valid_time = False
        return valid_time

    def on_begin(self):

        if not self.check_trading_hour():
            return

        today = datetime.today().date()
        last_market_day = today - timedelta(days=1)
        if today.weekday() == 0:
            # if monday
            last_market_day = today - timedelta(days=3)

        # hist top gainers
        top_gainers = HistoricalTopGainer.objects.filter(date=last_market_day)
        # update tracking_tickers
        for gainer in top_gainers:
            quote = webullsdk.get_quote(ticker_id=gainer.ticker_id)
            # weak open
            if 'open' in quote and float(quote['open']) <= gainer.price:
                key_stat = utils.get_hist_key_stat(
                    gainer.symbol, last_market_day)
                ticker = self.get_init_tracking_ticker(
                    gainer.symbol, gainer.ticker_id, prev_close=gainer.price, prev_high=key_stat.high)
                self.tracking_tickers[gainer.symbol] = ticker
                self.print_log("Add gainer <{}>[{}] to trade!".format(
                    gainer.symbol, gainer.ticker_id))
        # hist top losers
        top_losers = HistoricalTopLoser.objects.filter(date=last_market_day)
        # update tracking_tickers
        for loser in top_losers:
            quote = webullsdk.get_quote(ticker_id=loser.ticker_id)
            # weak open
            if 'open' in quote and float(quote['open']) <= loser.price:
                key_stat = utils.get_hist_key_stat(
                    loser.symbol, last_market_day)
                ticker = self.get_init_tracking_ticker(
                    loser.symbol, loser.ticker_id, prev_close=loser.price, prev_high=key_stat.high)
                self.tracking_tickers[loser.symbol] = ticker
                self.print_log("Add loser <{}>[{}] to trade!".format(
                    loser.symbol, loser.ticker_id))

    def on_update(self):
        if not self.check_trading_hour():
            return

        # only trade regular market hour before 13:00
        if utils.is_regular_market_hour() and datetime.now().hour <= 12:
            # trading tickers
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                # init stats
                self.init_ticker_stats(ticker)
                # do trade
                self.trade(ticker)
        elif not self.trading_end:
            # check if still holding any positions before exit
            while len(list(self.tracking_tickers)) > 0:
                for symbol in list(self.tracking_tickers):
                    ticker = self.tracking_tickers[symbol]
                    self.clear_position(ticker)

                # at least slepp 1 sec
                time.sleep(1)
            # save trading logs
            utils.save_trading_log(
                "\n".join(self.trading_logs), self.get_tag(), date.today())
            self.trading_end = True
