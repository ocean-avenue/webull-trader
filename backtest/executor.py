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
                 trading_hour: TradingHourType = TradingHourType.REGULAR, paper: bool = True):
        self.paper: bool = paper
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

        # prepare strategies
        for strategy in self.strategies:
            strategy.begin()

        while trading_time <= end_time:

            # go through strategies trades
            for strategy in self.strategies:
                if strategy.trading_end:
                    continue
                strategy.set_trading_time(trading_time)
                strategy.update()
                trading_logger.write(self.trading_hour, self.trading_date)

            trading_time = trading_time + timedelta(minutes=1)

        # finish strategies
        for strategy in self.strategies:
            strategy.end()

        # final round
        for strategy in self.strategies:
            strategy.final()

        trading_logger.log("Trading ended!")
        trading_logger.write(self.trading_hour, self.trading_date)

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
    from datetime import date
    from webull_trader.models import WebullAccountStatistics, WebullOrder, DayTrade, TradingLog
    from backtest.executor import BacktestExecutor
    from common.enums import TradingHourType
    from common import utils

    # remove all existing trades, orders
    WebullOrder.objects.all().delete()
    DayTrade.objects.all().delete()
    TradingLog.objects.all().delete()

    # backtest function
    def backtest(trading_date: date, trading_hour: TradingHourType):
        from trading.strategy.day_breakout import DayTradingBreakoutScale
        strategy = DayTradingBreakoutScale(
            paper=True, trading_hour=trading_hour, entry_period=20, exit_period=9)
        executor = BacktestExecutor(
            strategy=strategy, trading_date=trading_date, trading_hour=trading_hour, paper=True)
        print(
            f"[{utils.get_now()}] Backtesting for {trading_date} ({TradingHourType.tostr(trading_hour)})...")
        executor.start()

    trading_statistics = WebullAccountStatistics.objects.all()
    for trading_stat in trading_statistics:
        trading_stat: WebullAccountStatistics = trading_stat
        trading_date = trading_stat.date
        for trading_hour in [TradingHourType.BEFORE_MARKET_OPEN, TradingHourType.REGULAR, TradingHourType.AFTER_MARKET_CLOSE]:
            backtest(trading_date, trading_hour)


if __name__ == "django.core.management.commands.shell":
    start()
