# -*- coding: utf-8 -*-

# Trading executor class

import time
from datetime import datetime, timedelta
from webull_trader.enums import AlgorithmType, SetupType
from webull_trader.models import OvernightPosition, TradingSettings
from sdk import webullsdk
from scripts import utils


class TradingExecutor:

    def __init__(self, strategies=[], paper=True):
        self.paper = paper
        self.strategies = strategies

        self.unsold_tickers = {}

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
            # TODO, send message
            return
        print("[{}] Webull logged in".format(utils.get_now()))
        last_login_refresh_time = datetime.now()

        # check unsold tickers
        unsold_positions = OvernightPosition.objects.filter(
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

            # refresh login
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=self.refresh_login_interval_in_min):
                if webullsdk.login(paper=self.paper):
                    print("[{}] Refresh webull login".format(utils.get_now()))
                    last_login_refresh_time = datetime.now()
                else:
                    print("[{}] Webull refresh login failed, quit!".format(
                        utils.get_now()))
                    # TODO, send message
                    break

            # clear unsold positions
            self.clear_unsold_positions_update()

            # at least slepp 1 sec
            time.sleep(1)

        # finish strategies
        for strategy in self.strategies:
            strategy.on_end()

        # update account status
        account_data = webullsdk.get_account()
        utils.save_webull_account(account_data)

        # notify if has short position
        self.notify_if_has_short_positions()

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
        # pending order timeout in seconds
        self.pending_order_timeout_in_sec = trading_settings.pending_order_timeout_in_sec

        # init setting for strategies
        for strategy in self.strategies:
            strategy.load_settings(
                min_surge_amount=trading_settings.min_surge_amount,
                min_surge_volume=trading_settings.min_surge_volume,
                min_surge_change_ratio=trading_settings.min_surge_change_ratio,
                avg_confirm_volume=trading_settings.avg_confirm_volume,
                extended_avg_confirm_volume=trading_settings.extended_avg_confirm_volume,
                avg_confirm_amount=trading_settings.avg_confirm_amount,
                extended_avg_confirm_amount=trading_settings.extended_avg_confirm_amount,
                order_amount_limit=trading_settings.order_amount_limit,
                extended_order_amount_limit=trading_settings.extended_order_amount_limit,
                observe_timeout_in_sec=trading_settings.observe_timeout_in_sec,
                trade_interval_in_sec=trading_settings.trade_interval_in_sec,
                pending_order_timeout_in_sec=trading_settings.pending_order_timeout_in_sec,
                holding_order_timeout_in_sec=trading_settings.holding_order_timeout_in_sec,
                max_bid_ask_gap_ratio=trading_settings.max_bid_ask_gap_ratio,
                target_profit_ratio=trading_settings.target_profit_ratio,
                stop_loss_ratio=trading_settings.stop_loss_ratio,
                blacklist_timeout_in_sec=trading_settings.blacklist_timeout_in_sec,
                swing_position_amount_limit=trading_settings.swing_position_amount_limit,
                max_prev_day_close_gap_ratio=trading_settings.max_prev_day_close_gap_ratio,
                min_relative_volume=trading_settings.min_relative_volume,
                min_earning_gap_ratio=trading_settings.min_earning_gap_ratio,
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
                    if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                        # cancel timeout order
                        if webullsdk.cancel_order(ticker['pending_order_id']):
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
                    if 'msg' in order_response:
                        print(order_response['msg'])
                    elif 'orderId' in order_response:
                        # mark pending sell
                        self.unsold_tickers[symbol]['pending_sell'] = True
                        self.unsold_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        self.unsold_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                else:
                    # delete position object
                    self.unsold_tickers[symbol]['position_obj'].delete()
                    # not existed
                    del self.unsold_tickers[symbol]


def start():
    from scripts import utils
    from webull_trader.enums import AlgorithmType
    from trading.trading_executor import TradingExecutor
    from trading.day_momo import DayTradingMomo
    from trading.day_momo_reducesize import DayTradingMomoReduceSize
    # from trading.day_momo_newhigh import DayTradingMomoNewHigh
    from trading.day_momo_extendedhour import DayTradingMomoExtendedHour
    from trading.day_redgreen import DayTradingRedGreen
    from trading.day_breakout import DayTradingBreakout
    from trading.day_earnings_overnight import DayTradingEarningsOvernight
    from trading.swing_turtle import SwingTurtle

    paper = utils.check_paper()
    trading_hour = utils.get_trading_hour()
    if trading_hour == None:
        print("[{}] Not in trading hour, skip...".format(utils.get_now()))
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
        # DAY_BREAKOUT: breakout trade 10 minutes
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=10, exit_period=5))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_20:
        # DAY_BREAKOUT: breakout trade 20 minutes
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=20, exit_period=10))
    elif algo_type == AlgorithmType.DAY_BREAKOUT_30:
        # DAY_BREAKOUT: breakout trade 30 minutes
        strategies.append(DayTradingBreakout(
            paper=paper, trading_hour=trading_hour, entry_period=30, exit_period=15))
    elif algo_type == AlgorithmType.DAY_EARNINGS:
        # DAY_EARNINGS: earnings trade
        # TODO
        strategies.append(DayTradingEarningsOvernight(
            paper=paper, trading_hour=trading_hour))
    elif algo_type == AlgorithmType.DAY_EARNINGS_OVERNIGHT:
        # DAY_EARNINGS: earnings overnight trade
        strategies.append(DayTradingEarningsOvernight(
            paper=paper, trading_hour=trading_hour))
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
