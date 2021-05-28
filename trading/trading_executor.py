# -*- coding: utf-8 -*-

# Trading executor class

import time
from datetime import datetime, timedelta
from webull_trader.enums import AlgorithmType
from webull_trader.models import TradingSettings
from sdk import webullsdk
from scripts import utils


class TradingExecutor:

    def __init__(self, strategies=[], paper=True):
        self.paper = paper
        self.strategies = strategies

    def start(self):

        if not self.load_settings():
            print("[{}] Cannot find trading settings, quit!".format(
                utils.get_now()))
            return

        if len(self.strategies) == 0:
            print("[{}] Cannot find trading strategy, quit!".format(
                utils.get_now()))
            return

        print("[{}] Trading started...".format(utils.get_now()))

        print("[{}] {}".format(utils.get_now(),
              AlgorithmType.tostr(self.algo_type)))

        while not utils.is_market_hour():
            print("[{}] Waiting for market hour...".format(utils.get_now()))
            time.sleep(2)

        # login
        if not webullsdk.login(paper=self.paper):
            print("[{}] Webull login failed, quit!".format(
                utils.get_now()))
            return
        print("[{}] Webull logged in".format(utils.get_now()))
        last_login_refresh_time = datetime.now()

        # prepare strategies
        for strategy in self.strategies:
            strategy.on_begin()

        # main loop
        while utils.is_market_hour():
            # go through strategies trades
            for strategy in self.strategies:
                strategy.on_update()

            # refresh login
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=self.refresh_login_interval_in_min):
                webullsdk.login(paper=self.paper)
                print("[{}] Refresh webull login".format(utils.get_now()))
                last_login_refresh_time = datetime.now()

            # at least slepp 1 sec
            time.sleep(1)

        # finish strategies
        for strategy in self.strategies:
            strategy.on_end()

        print("[{}] Trading ended!".format(utils.get_now()))

        # output today's proft loss
        portfolio = webullsdk.get_portfolio()
        day_profit_loss = "-"
        if "dayProfitLoss" in portfolio:
            day_profit_loss = portfolio['dayProfitLoss']
        print("[{}] Today's P&L: {}".format(
            utils.get_now(), day_profit_loss))

        # webullsdk.logout()
        # print("[{}] Webull logged out".format(utils.get_now()))

    # load settings
    def load_settings(self):

        trading_settings = TradingSettings.objects.first()
        if not trading_settings:
            return False

        # algorithm type
        self.algo_type = trading_settings.algo_type
        # refresh login interval minutes
        self.refresh_login_interval_in_min = trading_settings.refresh_login_interval_in_min

        # init setting for strategies
        for strategy in self.strategies:
            strategy.load_settings(
                min_surge_amount=trading_settings.min_surge_amount,
                min_surge_volume=trading_settings.min_surge_volume,
                min_surge_change_ratio=trading_settings.min_surge_change_ratio,
                avg_confirm_volume=trading_settings.avg_confirm_volume,
                order_amount_limit=trading_settings.order_amount_limit,
                observe_timeout_in_sec=trading_settings.observe_timeout_in_sec,
                trade_interval_in_sec=trading_settings.trade_interval_in_sec,
                pending_order_timeout_in_sec=trading_settings.pending_order_timeout_in_sec,
                holding_order_timeout_in_sec=trading_settings.holding_order_timeout_in_sec,
                max_bid_ask_gap_ratio=trading_settings.max_bid_ask_gap_ratio,
                target_profit_ratio=trading_settings.target_profit_ratio,
                stop_loss_ratio=trading_settings.stop_loss_ratio,
                blacklist_timeout_in_sec=trading_settings.blacklist_timeout_in_sec,
            )
        return True


def start():
    from scripts import utils
    from webull_trader.enums import AlgorithmType
    from trading.trading_executor import TradingExecutor
    from trading.day_momo import DayTradingMomo
    from trading.day_momo_reducesize import DayTradingMomoReduceSize
    from trading.day_momo_newhigh import DayTradingMomoNewHigh
    from trading.day_redgreen import DayTradingRedGreen
    from trading.swing_turtle import SwingTurtle

    paper = utils.check_paper()
    strategies = []
    # load algo type
    algo_type = utils.get_algo_type()
    # load strategies
    if algo_type == AlgorithmType.DAY_MOMENTUM:
        # momo trade
        strategies.append(DayTradingMomo(paper=paper))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
        # momo trade with reduce size
        strategies.append(DayTradingMomoReduceSize(paper=paper))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_NEW_HIGH:
        # momo trade with new high confirm
        strategies.append(DayTradingMomoNewHigh(paper=paper))
    elif algo_type == AlgorithmType.DAY_RED_TO_GREEN:
        # red/green trade
        strategies.append(DayTradingRedGreen(paper=paper))
    elif algo_type == AlgorithmType.SWING_TURTLE_20:
        # turtle trade 20 days
        strategies.append(SwingTurtle(paper=paper, entry=20, exit=10))
    elif algo_type == AlgorithmType.SWING_TURTLE_55:
        # turtle trade 55 days
        strategies.append(SwingTurtle(paper=paper, entry=55, exit=20))
    elif algo_type == AlgorithmType.DAY_SWING_MOMO_TURTLE:
        # momo trade
        strategies.append(DayTradingMomo(paper=paper))
        # turtle trade 55 days
        strategies.append(SwingTurtle(paper=paper, entry=55, exit=20))
    elif algo_type == AlgorithmType.DAY_SWING_RG_TURTLE:
        # red/green trade
        strategies.append(DayTradingRedGreen(paper=paper))
        # turtle trade 55 days
        strategies.append(SwingTurtle(paper=paper, entry=55, exit=20))
    else:
        print("[{}] No trading job found, skip...".format(utils.get_now()))
        return
    executor = TradingExecutor(strategies=strategies, paper=paper)
    executor.start()


if __name__ == "django.core.management.commands.shell":
    start()
