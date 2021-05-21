# -*- coding: utf-8 -*-

# Momo day trading class

import time
from datetime import datetime, timedelta
from trading.base import TradingBase
from webull_trader.enums import SetupType, AlgorithmType
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser
from sdk import webullsdk
from scripts import utils


class DayTradingRedGreen(TradingBase):

    import pandas as pd

    def get_setup(self):
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker, m1_bars=pd.DataFrame()):
        # TODO
        pass

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
        if not webullsdk.login(paper=self.paper):
            print("[{}] Webull login failed, quit!".format(
                utils.get_now()))
            return
        print("[{}] Webull logged in".format(utils.get_now()))
        last_login_refresh_time = datetime.now()

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
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=self.refresh_login_interval_in_min):
                webullsdk.login(paper=self.paper)
                print("[{}] Refresh webull login".format(utils.get_now()))
                last_login_refresh_time = datetime.now()

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
