# -*- coding: utf-8 -*-

# Momo day trading class

import time
from datetime import datetime, timedelta
from trading.trading_base import TradingBase
from webull_trader.enums import SetupType, AlgorithmType
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser
from sdk import webullsdk
from scripts import utils


class DayTradingRedGreen(TradingBase):

    def get_setup(self):
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        prev_close = ticker['prev_close']

        # if ticker['pending_buy']:
        #     self.check_buy_order_filled(ticker)
        #     return

        # if ticker['pending_sell']:
        #     self.check_sell_order_filled(ticker)
        #     return

        holding_quantity = ticker['positions']

        # fetch 1m bar charts
        m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
        m2_bars = utils.convert_2m_bars(m1_bars)
        if m2_bars.empty:
            return

        current_candle = m2_bars.iloc[-1]
        prev_candle = m2_bars.iloc[-2]
        preprev_candle = m2_bars.iloc[-3]

        # current price data
        current_close = current_candle['close']
        current_low = current_candle['low']
        prev_low = prev_candle['low']
        preprev_volume = preprev_candle['volume']

        if holding_quantity == 0:

            # check entry: current price above prev close
            if current_low >= prev_close and prev_low <= prev_close:
                buy_position_amount = self.get_buy_order_limit(symbol)
                buy_quant = (int)(buy_position_amount / current_close)
                print("[{}] 🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                    utils.get_now(), symbol, ticker_id, buy_quant, current_close))
                # TODO
                self.tracking_tickers[symbol]['positions'] = buy_quant
        else:

            # check stop loss
            if current_close < prev_close:
                print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {} (STOP LOSS)".format(
                    utils.get_now(), symbol, ticker_id, holding_quantity, current_close))
                # TODO
                self.tracking_tickers[symbol]['positions'] = 0
                return

            # check taking profit
            take_profit = True
            for _, row in m2_bars.iterrows():
                if row['volume'] > preprev_volume:
                    take_profit = False
                    break
            if take_profit:
                print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {} (TAKE PROFIT)".format(
                    utils.get_now(), symbol, ticker_id, holding_quantity, current_close))
                # TODO
                self.tracking_tickers[symbol]['positions'] = 0
                return

    def print_algo_name(self):
        print("[{}] {}".format(utils.get_now(),
              AlgorithmType.tostr(AlgorithmType.DAY_RED_TO_GREEN)))

    def start(self):

        if not self.load_settings():
            print("[{}] Cannot find trading settings, quit!".format(
                utils.get_now()))
            return

        print("[{}] Trading started...".format(utils.get_now()))

        self.print_algo_name()

        while not utils.is_regular_market_hour():
            print("[{}] Waiting for market hour...".format(utils.get_now()))
            time.sleep(10)

        # login
        # TODO
        # if not webullsdk.login(paper=self.paper):
        #     print("[{}] Webull login failed, quit!".format(
        #         utils.get_now()))
        #     return
        # print("[{}] Webull logged in".format(utils.get_now()))
        # last_login_refresh_time = datetime.now()

        today = datetime.today().date()
        last_market_day = today - timedelta(days=1)
        if today.weekday() == 0:
            # if monday
            last_market_day = today - timedelta(days=3)

        # hist top gainers
        top_gainers = HistoricalTopGainer.objects.filter(date=last_market_day)
        # update tracking_tickers
        for gainer in top_gainers:
            ticker = self.get_init_tracking_ticker(
                gainer.symbol, gainer.ticker_id, prev_close=gainer.price)
            self.tracking_tickers[gainer.symbol] = ticker
            print("[{}] Add gainer <{}>[{}] to trade!".format(
                utils.get_now(), gainer.symbol, gainer.ticker_id))
        # hist top losers
        top_losers = HistoricalTopLoser.objects.filter(date=last_market_day)
        # update tracking_tickers
        for loser in top_losers:
            ticker = self.get_init_tracking_ticker(
                loser.symbol, loser.ticker_id, prev_close=loser.price)
            self.tracking_tickers[loser.symbol] = ticker
            print("[{}] Add loser <{}>[{}] to trade!".format(
                utils.get_now(), loser.symbol, loser.ticker_id))

        # main loop
        while utils.is_regular_market_hour():
            # trading tickers
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                # do trade
                self.trade(ticker)

            # refresh login
            # TODO
            # if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=self.refresh_login_interval_in_min):
            #     webullsdk.login(paper=self.paper)
            #     print("[{}] Refresh webull login".format(utils.get_now()))
            #     last_login_refresh_time = datetime.now()

            # at least slepp 1 sec
            time.sleep(1)

        # check if still holding any positions before exit
        while len(list(self.tracking_tickers)) > 0:
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                self.complete_order(ticker)

            # at least slepp 1 sec
            time.sleep(1)

        print("[{}] Trading ended!".format(utils.get_now()))

        # output today's proft loss
        portfolio = webullsdk.get_portfolio()
        day_profit_loss = "-"
        if "dayProfitLoss" in portfolio:
            day_profit_loss = portfolio['dayProfitLoss']
        print("[{}] Today's P&L: {}".format(
            utils.get_now(), day_profit_loss))


def start():
    from scripts import utils
    from trading.day_redgreen import DayTradingRedGreen

    paper = utils.check_paper()
    daytrading = DayTradingRedGreen(paper=paper)
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()
