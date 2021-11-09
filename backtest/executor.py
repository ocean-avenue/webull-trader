# -*- coding: utf-8 -*-

# Trading executor class

from datetime import datetime, timedelta, date
from common.enums import AlgorithmType, TradingHourType
from common import db
from logger import trading_logger
from backtest.strategy.strategy_base import BacktestStrategyBase


class BacktestExecutor:

    from common.enums import TradingHourType
    from datetime import date
    from backtest.strategy.strategy_base import BacktestStrategyBase

    def __init__(self, strategy: BacktestStrategyBase = None, trading_date: date = date.today(),
                 trading_hour: TradingHourType = TradingHourType.REGULAR):
        self.trading_date: date = trading_date
        self.trading_hour: TradingHourType = trading_hour
        self.strategy: BacktestStrategyBase = strategy
        # set trading time
        self.trading_time_range = [
            datetime(trading_date.year, trading_date.month,
                     trading_date.day, 9, 32),
            datetime(trading_date.year, trading_date.month,
                     trading_date.day, 15, 58),
        ]
        if trading_hour == TradingHourType.BEFORE_MARKET_OPEN:
            self.trading_time_range = [
                datetime(trading_date.year, trading_date.month,
                         trading_date.day, 4, 2),
                datetime(trading_date.year, trading_date.month,
                         trading_date.day, 9, 28),
            ]
        if trading_hour == TradingHourType.AFTER_MARKET_CLOSE:
            self.trading_time_range = [
                datetime(trading_date.year, trading_date.month,
                         trading_date.day, 16, 2),
                datetime(trading_date.year, trading_date.month,
                         trading_date.day, 19, 58),
            ]

    def start(self):

        self.load_settings()

        trading_logger.log("Trading started...")

        trading_logger.log(AlgorithmType.tostr(self.algo_type))

        trading_time, end_time = self.trading_time_range

        # prepare strategy
        self.strategy.begin()

        while trading_time <= end_time:

            self.strategy.set_trading_time(trading_time)
            # tick strategy
            self.strategy.update()
            trading_logger.write(self.trading_hour, self.trading_date)

            trading_time = trading_time + timedelta(minutes=1)

        # finish strategy
        self.strategy.end()

        # final round
        self.strategy.final()

        trading_logger.log("Trading ended!")
        trading_logger.write(self.trading_hour, self.trading_date)

    # load settings

    def load_settings(self):
        trading_settings = db.get_or_create_trading_settings()
        # algorithm type
        self.algo_type = trading_settings.algo_type
        # init setting for strategy
        self.strategy.load_settings(
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
    from datetime import date
    from webull_trader.models import WebullAccountStatistics, WebullOrder, DayTrade, DayPosition, TradingLog
    from backtest.executor import BacktestExecutor
    from common.enums import TradingHourType
    from common import utils, db
    from backtest.tracker import account_tracker
    from scripts import calculate_histdata

    # remove all existing trades, orders
    WebullOrder.objects.all().delete()
    DayTrade.objects.all().delete()
    DayPosition.objects.all().delete()
    TradingLog.objects.all().delete()

    # backtest function
    def backtest(trading_date: date, trading_hour: TradingHourType):
        from backtest.strategy.day_breakout import BacktestDayTradingBreakoutDynExit
        strategy = BacktestDayTradingBreakoutDynExit(
            trading_date=trading_date, trading_hour=trading_hour, entry_period=20, exit_period=9)
        # from backtest.strategy.day_scalping import BacktestDayTradingScalping
        # strategy = BacktestDayTradingScalping(
        #     trading_date=trading_date, trading_hour=trading_hour, entry_period=20)
        executor = BacktestExecutor(
            strategy=strategy, trading_date=trading_date, trading_hour=trading_hour)
        print(
            f"[{utils.get_now()}] Backtesting for {trading_date} ({TradingHourType.tostr(trading_hour)})...")
        executor.start()

    trading_statistics = WebullAccountStatistics.objects.all()
    for trading_stat in trading_statistics:
        trading_stat: WebullAccountStatistics = trading_stat
        trading_date = trading_stat.date
        for trading_hour in [TradingHourType.BEFORE_MARKET_OPEN, TradingHourType.REGULAR, TradingHourType.AFTER_MARKET_CLOSE]:
            backtest(trading_date, trading_hour)
        # calculate data
        calculate_histdata.start(day=trading_date)
        # save account stat
        db.save_webull_account(
            {
                "accountMembers": [
                    {
                        "key": "dayProfitLoss",
                        "value": db.get_hist_day_perf(day=trading_date).day_profit_loss,
                    },
                    {
                        "key": "usableCash",
                        "value": account_tracker.get_balance(),
                    },
                ],
                "netLiquidation": account_tracker.get_balance(),
                "totalProfitLoss": account_tracker.get_total_pl(),
                "totalProfitLossRate": account_tracker.get_total_pl_rate(),
            },
            paper=True,
            day=trading_date,
        )


if __name__ == "django.core.management.commands.shell":
    start()
