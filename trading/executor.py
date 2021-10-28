# -*- coding: utf-8 -*-

# Trading executor class

import time
from datetime import datetime, timedelta, date
from typing import List
from common.enums import AlgorithmType, TradingHourType
from common import utils, db, config, sms
from sdk import webullsdk
from logger import trading_logger
from trading.strategy.strategy_base import StrategyBase


class TradingExecutor:

    from typing import List
    from common.enums import TradingHourType
    from trading.strategy.strategy_base import StrategyBase

    def __init__(self, strategies: List[StrategyBase] = [],
                 trading_hour: TradingHourType = TradingHourType.REGULAR, paper: bool = True):
        self.paper: bool = paper
        self.trading_hour: TradingHourType = trading_hour
        self.strategies: List[StrategyBase] = strategies

    def start(self):

        self.load_settings()

        if len(self.strategies) == 0:
            trading_logger.log("Cannot find trading strategy, quit!")
            return

        trading_logger.log("Trading started...")

        trading_logger.log(AlgorithmType.tostr(self.algo_type))

        while not utils.is_market_hour():
            print("[{}] Waiting for market hour...".format(utils.get_now()))
            time.sleep(2)

        # login
        if not webullsdk.login(paper=self.paper):
            error_msg = "Webull login failed, quit trading!"
            # send message
            sms.notify_message(error_msg)
            trading_logger.log(error_msg)
            return
        trading_logger.log("Webull logged in")
        last_login_refresh_time = datetime.now()

        today = date.today()

        # prepare strategies
        for strategy in self.strategies:
            strategy.begin()

        # main loop
        while utils.is_market_hour():
            # go through strategies trades
            for strategy in self.strategies:
                if strategy.trading_end:
                    continue
                strategy.update_orders()
                strategy.update()
                trading_logger.write(self.trading_hour, today)

            # refresh login
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=config.REFRESH_LOGIN_INTERVAL_IN_MIN):
                if webullsdk.login(paper=self.paper):
                    # trading_logger.log("Refresh webull login")
                    last_login_refresh_time = datetime.now()
                else:
                    error_msg = "Webull refresh login failed, quit trading!"
                    # send message
                    sms.notify_message(error_msg)
                    trading_logger.log(error_msg)
                    break

            # at least slepp 1 sec
            time.sleep(1)

        # finish strategies
        while not utils.is_trading_hour_end(self.trading_hour):
            for strategy in self.strategies:
                strategy.end()
                trading_logger.write(self.trading_hour, today)

        # final round
        for strategy in self.strategies:
            strategy.final()
            trading_logger.write(self.trading_hour, today)

        # update account status
        account_data = webullsdk.get_account()
        db.save_webull_account(account_data, paper=self.paper)

        trading_logger.log("Trading ended!")

        # output today's proft loss
        day_profit_loss = webullsdk.get_day_profit_loss()
        trading_logger.log("Today's P&L: {}".format(day_profit_loss))

        trading_logger.write(self.trading_hour, today)

        # webullsdk.logout()
        # trading_logger.log("Webull logged out")

    # load settings
    def load_settings(self):
        trading_settings = db.get_or_create_trading_settings()
        # algorithm type
        self.algo_type = trading_settings.algo_type
        # init setting for strategies
        for strategy in self.strategies:
            strategy.load_settings(
                order_amount_limit=trading_settings.order_amount_limit,
                extended_order_amount_limit=trading_settings.extended_order_amount_limit,
                target_profit_ratio=trading_settings.target_profit_ratio,
                stop_loss_ratio=trading_settings.stop_loss_ratio,
                day_free_float_limit_in_million=trading_settings.day_free_float_limit_in_million,
                day_turnover_rate_limit_percentage=trading_settings.day_turnover_rate_limit_percentage,
                day_sectors_limit=trading_settings.day_sectors_limit,
                swing_position_amount_limit=trading_settings.swing_position_amount_limit,
                day_trade_usable_cash_threshold=trading_settings.day_trade_usable_cash_threshold,
            )


def start():
    from typing import List
    from common import utils
    from common.enums import AlgorithmType
    from trading.executor import TradingExecutor
    from trading.strategy.strategy_base import StrategyBase
    from trading.strategy.day_clean import DayTradingClean
    # from trading.day_momo import DayTradingMomoNewHigh
    from trading.strategy.day_momo import DayTradingMomo, DayTradingMomoShareSize, DayTradingMomoReduceSize, DayTradingMomoExtendedHour
    from trading.strategy.day_redgreen import DayTradingRedGreen
    from trading.strategy.day_breakout import DayTradingBreakout, DayTradingBreakoutAsk, DayTradingBreakoutDynExit, DayTradingBreakoutEarnings, \
        DayTradingBreakoutNewHigh, DayTradingBreakoutPeriod, DayTradingBreakoutPreLosers, DayTradingBreakoutScale, \
        DayTradingBreakoutScaleStopLossMax, DayTradingBreakoutScaleStopLossATR, DayTradingBreakoutScalePeriodROC
    from trading.strategy.day_earnings import DayTradingEarningsOvernight
    from trading.strategy.day_vwap import DayTradingVWAPPaper, DayTradingVWAPLargeCap
    from trading.strategy.day_grinding import DayTradingGrindingLargeCap, DayTradingGrindingSymbols
    from trading.strategy.swing_turtle import SwingTurtle

    paper = utils.is_paper_trading()
    trading_hour = utils.get_trading_hour()
    if trading_hour == None:
        trading_logger.log("Not in trading hour, skip...")
        return
    strategies: List[StrategyBase] = []
    # load algo type
    algo_type = utils.get_algo_type()
    if utils.is_day_trade_algo(algo_type):
        strategies.append(DayTradingClean(
            paper=paper, trading_hour=trading_hour))

    # load strategies
    if algo_type == AlgorithmType.DAY_MOMENTUM:
        # DAY_MOMENTUM: momo trade
        strategies.append(DayTradingMomo(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
        # DAY_MOMENTUM_REDUCE_SIZE: momo trade with reduce size
        strategies.append(DayTradingMomoReduceSize(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_SHARE_SIZE:
        # DAY_MOMENTUM_SHARE_SIZE: momo trade with same share size
        strategies.append(DayTradingMomoShareSize(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_NEW_HIGH:
        # DAY_MOMENTUM_NEW_HIGH: momo trade with new high confirm
        # strategies.append(DayTradingMomoNewHigh(paper=paper))
        strategies.append(DayTradingMomoExtendedHour(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_RED_TO_GREEN:
        # DAY_RED_TO_GREEN: red/green trade
        strategies.append(DayTradingRedGreen(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_10:
        # DAY_BREAKOUT: breakout trade 10 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20:
        # DAY_BREAKOUT: breakout trade 20 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=10))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20_11:
        # DAY_BREAKOUT: breakout trade 20,11 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=11))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20_9:
        # DAY_BREAKOUT: breakout trade 20,9 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20_8:
        # DAY_BREAKOUT: breakout trade 20,8 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=8))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20_1:
        # DAY_BREAKOUT: breakout trade 20,1 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=1))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_SCALE:
        # DAY_BREAKOUT: breakout trade 20 candles with scale in
        strategies.append(DayTradingBreakoutScale(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_PERIOD:
        # DAY_BREAKOUT: breakout trade 20 candles with period exit
        strategies.append(DayTradingBreakoutPeriod(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_DYNAMIC_EXIT:
        # DAY_BREAKOUT: breakout trade 20 candles with dynamic exit
        strategies.append(DayTradingBreakoutDynExit(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_SCALE_MAX_STOP_LOSS:
        # DAY_BREAKOUT: breakout trade 20 candles with scale in and max stop loss
        strategies.append(DayTradingBreakoutScaleStopLossMax(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_SCALE_ATR_STOP_LOSS:
        # DAY_BREAKOUT: breakout trade 20 candles with scale in and use ATR as stop loss
        strategies.append(DayTradingBreakoutScaleStopLossATR(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_SCALE_PERIOD_ROC:
        # DAY_BREAKOUT: breakout trade 20 candles with scale in and use period high for ROC check
        strategies.append(DayTradingBreakoutScalePeriodROC(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=9))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_30:
        # DAY_BREAKOUT: breakout trade 30 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=30, exit_period=15))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_55:
        # DAY_BREAKOUT: breakout trade 55 candles
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_NEW_HIGH:
        # DAY_BREAKOUT_NEW_HIGH: breakout trade with new high confirm
        strategies.append(DayTradingBreakoutNewHigh(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_10_5:
        # DAY_BREAKOUT_10_5: breakout trade with 5 minutes candles chart
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5, time_scale=5))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_PRE_LOSERS:
        # DAY_BREAKOUT_PRE_LOSERS: breakout trade with pre-market losers
        strategies.append(DayTradingBreakoutPreLosers(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_EARNINGS:
        # DAY_BREAKOUT_EARNINGS: breakout trade for earnings if earning day
        strategies.append(DayTradingBreakoutEarnings(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=10))
    elif algo_type == AlgorithmType.DAY_EARNINGS:
        # DAY_EARNINGS: earnings trade, dont include clean strategy
        strategies = [
            DayTradingEarningsOvernight(
                paper=paper, trading_hour=trading_hour)
        ]
    elif algo_type == AlgorithmType.DAY_EARNINGS_OVERNIGHT:
        # DAY_EARNINGS: earnings overnight trade
        strategies = [
            DayTradingEarningsOvernight(
                paper=paper, trading_hour=trading_hour)
        ]
    elif algo_type == AlgorithmType.DAY_VWAP_RECLAIM:
        # DAY_VWAP_RECLAIM: vwap reclaim day trade
        if paper:
            strategies.append(DayTradingVWAPPaper(
                paper=paper, trading_hour=trading_hour))
        else:
            # TODO, implement live vwap reclaim
            strategies.append(DayTradingVWAPPaper(
                paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_VWAP_RECLAIM_LARGE_CAP:
        # DAY_VWAP_RECLAIM_LARGE_CAP: vwap reclaim day trade with large cap
        strategies.append(DayTradingVWAPLargeCap(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_GRINDING_LARGE_CAP:
        # DAY_GRINDING_LARGE_CAP: grinding day trade with large cap
        strategies.append(DayTradingGrindingLargeCap(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_GRINDING_SYMBOLS:
        # DAY_GRINDING_SYMBOLS: grinding day trade with specific symbols
        strategies.append(DayTradingGrindingSymbols(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_ASK:
        # DAY_BREAKOUT_ASK: breakout trade with ask price limit order
        strategies.append(DayTradingBreakoutAsk(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=10))
    elif algo_type == AlgorithmType.SWING_TURTLE_20:
        # SWING_TURTLE_20: turtle trade 20 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=10))
    elif algo_type == AlgorithmType.SWING_TURTLE_55:
        # SWING_TURTLE_55: turtle trade 55 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    elif algo_type == AlgorithmType.DAY_SWING_MOMO_TURTLE:
        # DAY_SWING_MOMO_TURTLE:
        # momo trade
        strategies.append(DayTradingMomo(
            paper=paper, trading_hour=trading_hour))
        # turtle trade 55 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    elif algo_type == AlgorithmType.DAY_SWING_RG_TURTLE:
        # DAY_SWING_RG_TURTLE
        # red/green trade
        strategies.append(DayTradingRedGreen(
            paper=paper, trading_hour=trading_hour))
        # turtle trade 55 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    elif algo_type == AlgorithmType.DAY_SWING_EARNINGS_TURTLE:
        # DAY_SWING_EARNINGS_TURTLE
        # earnings trade
        strategies = [
            DayTradingEarningsOvernight(
                paper=paper, trading_hour=trading_hour)
        ]
        # turtle trade 55 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    elif algo_type == AlgorithmType.DAY_SWING_BREAKOUT_TURTLE:
        # DAY_SWING_BREAKOUT_TURTLE
        # breakout trade
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5))
        # turtle trade 55 days
        strategies.append(SwingTurtle(
            paper=paper, trading_hour=trading_hour, entry_period=55, exit_period=20))
    else:
        print("[{}] No trading job found, skip...".format(utils.get_now()))
        return
    executor = TradingExecutor(
        strategies=strategies, trading_hour=trading_hour, paper=paper)
    executor.start()


if __name__ == "django.core.management.commands.shell":
    start()
