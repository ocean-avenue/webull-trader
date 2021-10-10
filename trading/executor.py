# -*- coding: utf-8 -*-

# Trading executor class

import time
from datetime import datetime, timedelta
from webull_trader.enums import AlgorithmType, SetupType
from webull_trader.models import DayPosition, TradingSettings
from sdk import webullsdk
from scripts import utils, config


class TradingExecutor:

    def __init__(self, strategies=[], paper=True):
        self.paper = paper
        self.strategies = strategies

        self.unsold_tickers = {}

    def start(self):

        if not self.load_settings():
            utils.print_trading_log("Cannot find trading settings, quit!")
            return

        if len(self.strategies) == 0:
            utils.print_trading_log("Cannot find trading strategy, quit!")
            return

        utils.print_trading_log("Trading started...")

        utils.print_trading_log(AlgorithmType.tostr(self.algo_type))

        while not utils.is_market_hour():
            print("[{}] Waiting for market hour...".format(utils.get_now()))
            time.sleep(2)

        # login
        if not webullsdk.login(paper=self.paper):
            message = "Webull login failed, quit trading!"
            # send message
            utils.notify_message(message)
            utils.print_trading_log(message)
            return
        utils.print_trading_log("Webull logged in")
        last_login_refresh_time = datetime.now()

        # check unsold tickers
        unsold_positions = DayPosition.objects.filter(
            setup=SetupType.ERROR_FAILED_TO_SELL)
        for position in unsold_positions:
            self.unsold_tickers[position.symbol] = {
                "symbol": position.symbol,
                "ticker_id": position.ticker_id,
                "pending_sell": False,
                "pending_order_id": None,
                "pending_order_time": None,
                "positions": position.quantity,
                "position_obj": position,
            }

        # prepare strategies
        for strategy in self.strategies:
            strategy.on_begin()

        # main loop
        while utils.is_market_hour():
            # go through strategies trades
            for strategy in self.strategies:
                if not strategy.trading_end:
                    strategy.on_update()
                    strategy.save_logs()

            # refresh login
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=config.REFRESH_LOGIN_INTERVAL_IN_MIN):
                if webullsdk.login(paper=self.paper):
                    # utils.print_trading_log("Refresh webull login")
                    last_login_refresh_time = datetime.now()
                else:
                    message = "Webull refresh login failed, quit trading!"
                    # send message
                    utils.notify_message(message)
                    utils.print_trading_log(message)
                    break

            # clear unsold positions
            self.clear_unsold_positions_update()

            # at least slepp 1 sec
            time.sleep(1)

        # finish strategies
        for strategy in self.strategies:
            strategy.on_end()
            strategy.save_logs()

        # update account status
        account_data = webullsdk.get_account()
        utils.save_webull_account(account_data, paper=self.paper)

        # notify if has short position
        self.notify_if_has_short_positions()

        utils.print_trading_log("Trading ended!")

        # output today's proft loss
        day_profit_loss = webullsdk.get_day_profit_loss()
        utils.print_trading_log("Today's P&L: {}".format(day_profit_loss))

        # webullsdk.logout()
        # utils.print_trading_log("Webull logged out")

    # load settings
    def load_settings(self):

        trading_settings = TradingSettings.objects.first()
        if not trading_settings:
            return False

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
        return True

    # notify me if has short positions
    def notify_if_has_short_positions(self):
        # TODO, send messages
        pass

    def clear_unsold_positions_update(self):
        if len(self.unsold_tickers) == 0:
            return
        positions = webullsdk.get_positions()
        if positions == None:
            return
        for symbol in list(self.unsold_tickers):
            ticker = self.unsold_tickers[symbol]
            # check if already sold
            if ticker['pending_sell']:
                order_filled = True
                for position in positions:
                    # make sure position is positive
                    if position['ticker']['symbol'] == symbol and float(position['position']) > 0:
                        order_filled = False
                        break
                if order_filled:
                    # delete position object
                    self.unsold_tickers[symbol]['position_obj'].delete()
                    # order filled
                    del self.unsold_tickers[symbol]
                else:
                    # check order timeout
                    if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=config.PENDING_ORDER_TIMEOUT_IN_SEC):
                        # cancel timeout order
                        if webullsdk.cancel_order(ticker['pending_order_id']) or webullsdk.check_order_canceled(ticker['pending_order_id']):
                            # reset
                            self.unsold_tickers[symbol]['pending_sell'] = False
                            self.unsold_tickers[symbol]['pending_order_id'] = None
                            self.unsold_tickers[symbol]['pending_order_time'] = None

            else:
                # check the position is existed
                existed = False
                for position in positions:
                    # make sure position is positive
                    if position['ticker']['symbol'] == symbol and float(position['position']) > 0:
                        existed = True
                        break
                if existed:
                    quote = webullsdk.get_quote(ticker_id=ticker['ticker_id'])
                    if quote == None:
                        return
                    bid_price = webullsdk.get_bid_price_from_quote(quote)
                    if bid_price == None:
                        return
                    order_response = webullsdk.sell_limit_order(
                        ticker_id=ticker['ticker_id'],
                        price=bid_price,
                        quant=ticker['positions'])

                    order_id = utils.get_order_id_from_response(
                        order_response, paper=self.paper)
                    if order_id:
                        # mark pending sell
                        self.unsold_tickers[symbol]['pending_sell'] = True
                        self.unsold_tickers[symbol]['pending_order_id'] = order_id
                        self.unsold_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                    else:
                        utils.print_trading_log(
                            "⚠️  Invalid sell order response: {}".format(order_response))
                else:
                    # delete position object
                    self.unsold_tickers[symbol]['position_obj'].delete()
                    # not existed
                    del self.unsold_tickers[symbol]


def start():
    from scripts import utils
    from webull_trader.enums import AlgorithmType
    from trading.executor import TradingExecutor
    # from trading.day_momo import DayTradingMomoNewHigh
    from trading.day_momo import DayTradingMomo, DayTradingMomoReduceSize, DayTradingMomoExtendedHour
    from trading.day_redgreen import DayTradingRedGreen
    from trading.day_breakout import DayTradingBreakout, DayTradingBreakoutAsk, DayTradingBreakoutDynExit, DayTradingBreakoutEarnings, \
        DayTradingBreakoutNewHigh, DayTradingBreakoutPeriod, DayTradingBreakoutPreLosers, DayTradingBreakoutScale, \
        DayTradingBreakoutScaleStopLossMax, DayTradingBreakoutScaleStopLossATR, DayTradingBreakoutScalePeriodROC
    from trading.day_earnings import DayTradingEarningsOvernight
    from trading.day_vwap import DayTradingVWAPPaper, DayTradingVWAPLargeCap
    from trading.day_grinding import DayTradingGrindingLargeCap, DayTradingGrindingSymbols
    from trading.swing_turtle import SwingTurtle

    paper = utils.check_paper()
    trading_hour = utils.get_trading_hour()
    if trading_hour == None:
        utils.print_trading_log("Not in trading hour, skip...")
        return
    strategies = []
    # load algo type
    algo_type = utils.get_algo_type()
    # load strategies
    if algo_type == AlgorithmType.DAY_MOMENTUM:
        # DAY_MOMENTUM: momo trade
        strategies.append(DayTradingMomo(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_MOMENTUM_REDUCE_SIZE:
        # DAY_MOMENTUM_REDUCE_SIZE: momo trade with reduce size
        strategies.append(DayTradingMomoReduceSize(
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
        # DAY_EARNINGS: earnings trade
        strategies.append(DayTradingEarningsOvernight(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_EARNINGS_OVERNIGHT:
        # DAY_EARNINGS: earnings overnight trade
        strategies.append(DayTradingEarningsOvernight(
            paper=paper, trading_hour=trading_hour))
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
        strategies.append(DayTradingEarningsOvernight(
            paper=paper, trading_hour=trading_hour))
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
    executor = TradingExecutor(strategies=strategies, paper=paper)
    executor.start()


if __name__ == "django.core.management.commands.shell":
    start()
