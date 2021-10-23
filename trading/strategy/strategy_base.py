# -*- coding: utf-8 -*-

# Base trading class

import json
import pandas as pd
from datetime import datetime, timedelta, date
from django.utils import timezone
from sdk import webullsdk, fmpsdk
from common import utils, db, config, constants, exceptions
from common.enums import ActionType, SetupType, TradingHourType
from trading.tracker.trading_tracker import TradingTracker, TrackingTicker
from trading.tracker.order_tracker import OrderTracker
from trading.tracker.position_tracker import PositionTracker
from webull_trader.models import DayPosition, SwingPosition, SwingTrade


class StrategyBase:

    def __init__(self, paper: bool = True, trading_hour: TradingHourType = TradingHourType.REGULAR):
        self.paper: bool = paper
        self.trading_hour: TradingHourType = trading_hour
        self.trading_end: bool = False
        self.trading_tracker: TradingTracker = TradingTracker()
        self.order_tracker: OrderTracker = OrderTracker()
        self.position_tracker: PositionTracker = PositionTracker()
        # init trading variables
        # TODO, remove
        # may have error short sell due to latency
        self.error_short_tickers = {}
        # sometime system may not cancel order correctly
        self.canceled_orders = {}
        # init trading logs
        utils.TRADING_LOGS = []

    def begin(self):
        pass

    def update(self):
        pass

    def end(self):
        pass

    def get_tag(self) -> str:
        return "StrategyBase"

    def get_setup(self) -> SetupType:
        return SetupType.UNKNOWN

    # load settings
    def load_settings(self,
                      order_amount_limit: float,
                      extended_order_amount_limit: float,
                      target_profit_ratio: float,
                      stop_loss_ratio: float,
                      day_free_float_limit_in_million: float,
                      day_turnover_rate_limit_percentage: float,
                      day_sectors_limit: str,
                      swing_position_amount_limit: float,
                      day_trade_usable_cash_threshold: float):

        self.order_amount_limit: float = order_amount_limit
        utils.print_trading_log(
            "Buy order limit: {}".format(self.order_amount_limit))

        self.extended_order_amount_limit: float = extended_order_amount_limit
        utils.print_trading_log("Buy order limit (extended hour): {}".format(
            self.extended_order_amount_limit))

        self.target_profit_ratio: float = target_profit_ratio
        utils.print_trading_log("Target profit rate: {}%".format(
            round(self.target_profit_ratio * 100, 2)))

        self.stop_loss_ratio: float = stop_loss_ratio
        utils.print_trading_log("Stop loss rate: {}%".format(
            round(self.stop_loss_ratio * 100, 2)))

        self.day_free_float_limit_in_million: float = day_free_float_limit_in_million
        utils.print_trading_log("Day trading max free float (million): {}".format(
            self.day_free_float_limit_in_million))

        self.day_turnover_rate_limit_percentage: float = day_turnover_rate_limit_percentage
        utils.print_trading_log("Day trading min turnover rate: {}%".format(
            self.day_turnover_rate_limit_percentage))

        self.day_sectors_limit: str = day_sectors_limit
        utils.print_trading_log("Day trading sectors limit: {}".format(
            self.day_sectors_limit))

        self.swing_position_amount_limit: float = swing_position_amount_limit
        utils.print_trading_log("Swing position amount limit: {}".format(
            self.swing_position_amount_limit))

        self.day_trade_usable_cash_threshold: float = day_trade_usable_cash_threshold
        utils.print_trading_log("Usable cash threshold for day trade: {}".format(
            self.day_trade_usable_cash_threshold))

    def update_orders(self):
        # update order tracker
        self.order_tracker.update_orders()

    def update_positions(self):
        # update positions
        self.position_tracker.update_positions()

    def write_logs(self):
        # save trading logs
        # TODO, trading log based on algo
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())

    def build_error_short_ticker(self, symbol, ticker_id):
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            # pending buy back order id
            "pending_order_id": None,
            # pending buy back order time
            "pending_order_time": None,
        }

    def is_regular_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.REGULAR

    def is_pre_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.BEFORE_MARKET_OPEN

    def is_after_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.AFTER_MARKET_CLOSE

    def is_extended_market_hour(self) -> bool:
        return self.is_pre_market_hour() or self.is_after_market_hour()

    def check_can_trade_ticker(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        settings = db.get_or_create_trading_settings()
        day_free_float_limit_in_million = settings.day_free_float_limit_in_million
        day_turnover_rate_limit_percentage = settings.day_turnover_rate_limit_percentage
        tracking_status = self.trading_tracker.get_status(symbol)
        # fetch data if not cached
        if day_free_float_limit_in_million > 0 or day_turnover_rate_limit_percentage > 0:
            if tracking_status.get_free_float() == None or tracking_status.get_turnover_rate() == None:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                tracking_status.set_free_float(
                    utils.get_attr_to_float_or_none(quote, "outstandingShares"))
                tracking_status.set_turnover_rate(
                    utils.get_attr_to_float_or_none(quote, "turnoverRate"))
        free_float_check = True
        if day_free_float_limit_in_million > 0:
            if tracking_status.get_free_float() == None or \
                    tracking_status.get_free_float() > day_free_float_limit_in_million * constants.ONE_MILLION:
                free_float_check = False
        turnover_rate_check = True
        if day_turnover_rate_limit_percentage > 0:
            if tracking_status.get_turnover_rate() == None or \
                    tracking_status.get_turnover_rate() * constants.ONE_HUNDRED < day_turnover_rate_limit_percentage:
                turnover_rate_check = False
        sectors_check = True
        day_sectors_limit = settings.day_sectors_limit
        if len(day_sectors_limit) > 0:
            # fetch sector if not cached
            if tracking_status.get_sector() == None:
                profile = fmpsdk.get_profile(symbol)
                if profile and "sector" in profile:
                    tracking_status.set_sector(profile["sector"])
            sectors_limit = day_sectors_limit.split(",")
            if tracking_status.get_sector() == None or tracking_status.get_sector() not in sectors_limit:
                sectors_check = False

        return (free_float_check or turnover_rate_check) and sectors_check

    def check_error_short_order(self, positions):
        # check if short order covered
        for symbol in list(self.error_short_tickers):
            ticker = self.error_short_tickers[symbol]
            ticker_id = ticker['ticker_id']
            order_filled = True
            for position in positions:
                # make sure is short position
                if position['ticker']['symbol'] == symbol and float(position['position']) < 0:
                    order_filled = False
                    break
            if order_filled:
                # remove
                del self.error_short_tickers[symbol]
                utils.print_trading_log(
                    "Short cover order <{}> filled".format(symbol))
            else:
                # check order timeout
                if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=config.PENDING_ORDER_TIMEOUT_IN_SEC):
                    # cancel timeout order
                    if webullsdk.cancel_order(ticker['pending_order_id']) or webullsdk.check_order_canceled(ticker['pending_order_id']):
                        # remove, let function re-submit again
                        del self.error_short_tickers[symbol]
                    else:
                        utils.print_trading_log(
                            "Failed to cancel timeout short cover order <{}>!".format(symbol))
        for position in positions:
            # if short position
            position_size = int(position['position'])
            if position_size < 0:
                symbol = position['ticker']['symbol']
                ticker_id = position['ticker']['tickerId']
                if symbol not in self.error_short_tickers:
                    self.error_short_tickers[symbol] = self.build_error_short_ticker(
                        symbol, ticker_id)
                    last_price = float(position['lastPrice'])
                    # in order to buy, increase 1% to buy
                    buy_price = round(last_price*1.01, 2)
                    # submit buy back order
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=buy_price,
                        quant=abs(position_size))
                    utils.print_trading_log("🟢 Submit short cover order <{}>, quant: {}, limit price: {}".format(
                        symbol, abs(position_size), buy_price))
                    order_id = utils.get_order_id_from_response(
                        order_response, paper=self.paper)
                    if order_id:
                        self.error_short_tickers[symbol]['pending_order_id'] = order_id
                        self.error_short_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                    else:
                        utils.print_trading_log(
                            "⚠️  Invalid short cover order response: {}".format(order_response))

    # check if have failed to cancel order positions
    def check_error_cancel_order(self, positions):
        for position in positions:
            symbol = position['ticker']['symbol']
            # still in tracking
            if self.trading_tracker.is_tracking(symbol):
                continue
            # handling in short positions
            if symbol in self.error_short_tickers:
                continue
            # is day position
            if DayPosition.objects.filter(symbol=symbol).first():
                continue
            # is swing position
            if SwingPosition.objects.filter(symbol=symbol).first():
                continue
            ticker_id = position['ticker']['tickerId']
            ticker = TrackingTicker(symbol, ticker_id)
            ticker.set_positions(int(position['position']))
            ticker.set_last_buy_time(datetime.now())
            ticker.set_initial_cost(float(position['costPrice']))
            order_id = utils.get_attr_to_num(self.canceled_orders, symbol)
            # save order note
            # TODO, remove
            utils.save_webull_order_note(
                order_id,
                setup=SetupType.ERROR_FAILED_TO_CANCEL_ORDER,
                note="Failed to cancel buy order")
            # recover day position
            position_obj = utils.add_day_position(
                symbol=symbol,
                ticker_id=ticker_id,
                order_id=order_id,
                setup=SetupType.ERROR_FAILED_TO_CANCEL_ORDER,
                cost=float(position['costPrice']),
                quant=int(position['position']),
                buy_time=timezone.now(),
            )
            ticker.set_position_obj(position_obj)
            # recover tracking
            self.trading_tracker.start_tracking(ticker)

    def submit_buy_limit_order(self, ticker: TrackingTicker, note: str = "Entry point.",
                               retry: bool = False, retry_limit: int = 0):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            utils.print_trading_log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_price = self.get_buy_price(ticker)
        buy_quant = (int)(buy_position_amount / buy_price)
        if buy_quant > 0:
            # submit limit order at ask price
            order_response = webullsdk.buy_limit_order(
                ticker_id=ticker_id,
                price=buy_price,
                quant=buy_quant)
            utils.print_trading_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                symbol, buy_quant, buy_price))
            # tracking pending buy order
            self.start_tracking_pending_buy_order(
                ticker, order_response, entry_note=note, retry=retry, retry_limit=retry_limit)
        else:
            utils.print_trading_log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

    def submit_sell_limit_order(self, ticker: TrackingTicker, note: str = "Exit point.",
                                retry: bool = True, retry_limit: int = 20):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        holding_quantity = ticker.get_positions()
        sell_price = self.get_sell_price(ticker)
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=sell_price,
            quant=holding_quantity)
        utils.print_trading_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
            symbol, holding_quantity, sell_price))
        # tracking pending sell order
        self.start_tracking_pending_sell_order(
            ticker, order_response, exit_note=note, retry=retry, retry_limit=retry_limit)
        # update trading stats
        # TODO, tracking status when order done
        # self.update_trading_stats(
        #     ticker, last_price, cost_price, profit_loss_rate)

    def check_buy_order_done(self, ticker: TrackingTicker,
                             stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            return
        utils.print_trading_log(f"Buy order <{symbol}> {order.status}")
        # filled or partially filled
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            position_obj = ticker.get_position_obj()
            if position_obj:
                # update position obj
                position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
                position_obj.quantity += order.filled_quantity
                position_obj.total_cost += round(
                    order.filled_quantity * order.avg_price, 2)
                position_obj.units += 1
                position_obj.require_adjustment = True
                position_obj.save()
            else:
                # create position obj
                position_obj = db.add_day_position(
                    symbol=symbol,
                    ticker_id=ticker_id,
                    order_id=order_id,
                    setup=self.get_setup(),
                    cost=order.avg_price,
                    quant=order.filled_quantity,
                    buy_time=order.filled_time,
                    stop_loss_price=ticker.get_stop_loss(),
                    target_units=ticker.get_target_units(),
                )
                # set position obj
                ticker.set_position_obj(position_obj)
                # set initial cost
                ticker.set_initial_cost(order.avg_price)
            ticker.set_positions(position_obj.quantity)
            ticker.reset_resubmit_order_count()
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout() or self.trading_end:
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Buy order timeout, canceled!")
                else:
                    utils.print_trading_log(
                        f"Failed to cancel timeout buy <{symbol}> order: {order_id}!")
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
        # unknown status
        else:
            # TODO, log exception
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}' for order: {order_id}!")

    def check_sell_order_done(self, ticker: TrackingTicker,
                              stop_tracking_ticker_after_order_filled: bool = True):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            return
        utils.print_trading_log(f"Sell order <{symbol}> {order.status}")
        # filled
        if order.status == webullsdk.ORDER_STATUS_FILLED:
            position_obj = ticker.get_position_obj()
            # add trade object
            db.add_day_trade(
                symbol=symbol,
                ticker_id=ticker_id,
                position_obj=position_obj,
                order_id=order_id,
                sell_price=order.avg_price,
                sell_time=order.filled_time,
            )
            # remove position object
            position_obj.delete()
            ticker.set_position_obj(None)
            ticker.set_positions(0)
            ticker.reset_resubmit_order_count()
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)
            # update account status
            account_data = webullsdk.get_account()
            db.save_webull_account(account_data, paper=self.paper)
        # partially filled
        elif order.status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED:
            position_obj = ticker.get_position_obj()
            # update position object
            position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
            position_obj.require_adjustment = True
            position_obj.save()
            # update tracking ticker
            holding_quantity = ticker.get_positions() - order.filled_quantity
            ticker.set_positions(holding_quantity)
            ticker.reset_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # continue sell reset positions
            utils.print_trading_log(
                f"Continue sell rest <{symbol}> positions, quant: {holding_quantity}")
            self.submit_sell_limit_order(
                ticker, note="Sell rest positions.", retry=retry_after_cancel, retry_limit=retry_limit)
            # update account status
            account_data = webullsdk.get_account()
            db.save_webull_account(account_data, paper=self.paper)
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout():
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Sell order timeout, canceled!")
                else:
                    utils.print_trading_log(
                        f"Failed to cancel timeout sell <{symbol}> order: {order_id}!")
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            resubmit_count = ticker.get_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                # retry sell order
                utils.print_trading_log(
                    f"Resubmitting sell order <{symbol}>...")
                self.submit_sell_limit_order(
                    ticker, note=f"Resubmit sell order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                # increment resubmit order count
                ticker.inc_resubmit_order_count()
            else:
                position_obj = ticker.get_position_obj()
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                utils.print_trading_log(
                    "Failed to sell position <{}>!".format(symbol))
                # send message
                utils.notify_message(
                    "Failed to sell <{}> position, please check now!".format(symbol))
                # stop tracking ticker
                if stop_tracking_ticker_after_order_filled:
                    self.trading_tracker.stop_tracking(ticker)
            self.stop_tracking_pending_sell_order(ticker, order_id)
        # unknown status
        else:
            # TODO, log exception
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}' for order: {order_id}!")

    def check_cancel_order_done(self, ticker: TrackingTicker,
                                stop_tracking_ticker_after_order_canceled: bool = False):
        symbol = ticker.get_symbol()
        utils.print_trading_log(
            "Checking cancel order <{}> done...".format(symbol))
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if not order:
            # TODO, log exception
            raise exceptions.WebullOrderNotFoundError()
        # failed or canceled
        if order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking cancel order
            self.stop_tracking_pending_cancel_order(ticker, order_id)
            resubmit_count = ticker.get_resubmit_order_count()
            retry_after_cancel, retry_limit = self.order_tracker.check_retry_after_cancel(
                order_id)
            # buy order
            if order.action == ActionType.BUY:
                if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                    # retry buy order
                    utils.print_trading_log(
                        f"Resubmitting buy order <{symbol}>...")
                    self.submit_buy_limit_order(
                        ticker, note=f"Resubmit buy order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                    # increment resubmit order count
                    ticker.inc_resubmit_order_count()
                else:
                    if stop_tracking_ticker_after_order_canceled:
                        self.trading_tracker.stop_tracking(ticker)
            # sell order
            if order.action == ActionType.SELL:
                if retry_after_cancel and resubmit_count < retry_limit and not self.trading_end:
                    # retry sell order
                    utils.print_trading_log(
                        f"Resubmitting sell order <{symbol}>...")
                    self.submit_sell_limit_order(
                        ticker, note=f"Resubmit sell order ({resubmit_count}).", retry=retry_after_cancel, retry_limit=retry_limit)
                    # increment resubmit order count
                    ticker.inc_resubmit_order_count()
                else:
                    position_obj = ticker.get_position_obj()
                    # update setup
                    position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                    position_obj.save()
                    utils.print_trading_log(
                        "Failed to sell position <{}>!".format(symbol))
                    # send message
                    utils.notify_message(
                        "Failed to sell <{}> position, please check now!".format(symbol))
                    if stop_tracking_ticker_after_order_canceled:
                        self.trading_tracker.stop_tracking(ticker)
        elif ticker.is_order_timeout():
            # TODO, log exception
            raise exceptions.WebullOrderStatusError(
                f"Error cancel order status '{order.status}' for order {order_id}")

    def update_trading_stats(self, ticker, price, cost, profit_loss_rate):
        symbol = ticker['symbol']
        # after perform 1 trade
        self.tracking_stats[symbol]['trades'] += 1
        self.tracking_stats[symbol]['last_trade_time'] = datetime.now()
        last_high_price = self.tracking_stats[symbol]['last_high_price'] or 0
        self.tracking_stats[symbol]['last_high_price'] = max(
            cost, price, last_high_price)
        if profit_loss_rate > 0:
            self.tracking_stats[symbol]['win_trades'] += 1
            self.tracking_stats[symbol]['continue_lose_trades'] = 0
        else:
            self.tracking_stats[symbol]['lose_trades'] += 1
            self.tracking_stats[symbol]['continue_lose_trades'] += 1

    def start_tracking_pending_buy_order(self, ticker: TrackingTicker, order_response: dict, entry_note: str = "",
                                         retry: bool = False, retry_limit: int = 0):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            ticker.reset_pending_order()
            # mark pending buy
            ticker.set_pending_buy(True)
            ticker.set_pending_order_id(order_id)
            ticker.set_pending_order_time(datetime.now())
            # tracking order
            self.order_tracker.start_tracking(
                order_id, self.get_setup(), entry_note, retry, retry_limit)
        else:
            utils.print_trading_log(
                "⚠️  Invalid buy order response: {}".format(order_response))

    def stop_tracking_pending_buy_order(self, ticker: TrackingTicker, order_id: str):
        ticker.reset_pending_order()
        ticker.set_last_buy_time(datetime.now())
        self.order_tracker.stop_tracking(order_id)

    def start_tracking_pending_sell_order(self, ticker: TrackingTicker, order_response: dict, exit_note: str = "",
                                          retry: bool = True, retry_limit: int = 20):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            ticker.reset_pending_order()
            # mark pending sell
            ticker.set_pending_sell(True)
            ticker.set_pending_order_id(order_id)
            ticker.set_pending_order_time(datetime.now())
            # tracking order
            self.order_tracker.start_tracking(
                order_id, self.get_setup(), exit_note, retry, retry_limit)
        else:
            utils.print_trading_log(
                "⚠️  Invalid sell order response: {}".format(order_response))

    def stop_tracking_pending_sell_order(self, ticker: TrackingTicker, order_id: str):
        ticker.reset_pending_order()
        ticker.set_last_sell_time(datetime.now())
        self.order_tracker.stop_tracking(order_id)

    def start_tracking_pending_cancel_order(self, ticker: TrackingTicker, order_id: str, cancel_note: str = ""):
        ticker.reset_pending_order()
        # mark pending sell
        ticker.set_pending_cancel(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id, self.get_setup(), cancel_note)

    def stop_tracking_pending_cancel_order(self, ticker: TrackingTicker, order_id: str):
        ticker.reset_pending_order()
        self.order_tracker.stop_tracking(order_id)

    def update_pending_swing_position(self, symbol, order_response, position, cost, quant, buy_time, setup):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            if not position:
                # create swing position
                position = SwingPosition(
                    symbol=symbol,
                    order_ids=order_id,
                    total_cost=cost * quant,
                    quantity=quant,
                    units=1,
                    buy_time=buy_time,
                    buy_date=buy_time.date(),
                    setup=setup,
                    require_adjustment=True,
                )
            else:
                # update swing position for add unit
                position.order_ids = "{},{}".format(
                    position.order_ids, order_id)
                position.total_cost = position.total_cost + cost * quant
                position.quantity = position.quantity + quant
                position.units = position.units + 1
                # temp add unit, stop loss price
                position.add_unit_price = constants.MAX_SECURITY_PRICE
                position.stop_loss_price = 0
                position.require_adjustment = True
            position.save()
        else:
            utils.print_trading_log(
                "⚠️  Invalid swing buy order response: {}".format(order_response))

    def update_pending_swing_trade(self, symbol, order_response, position, price, sell_time, manual_request=None):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            order_ids = "{},{}".format(position.order_ids, order_id)
            # create swing position
            trade = SwingTrade(
                symbol=symbol,
                order_ids=order_ids,
                total_cost=position.total_cost,
                total_sold=price * position.quantity,
                quantity=position.quantity,
                units=position.units,
                buy_time=position.buy_time,
                buy_date=position.buy_date,
                sell_time=sell_time,
                sell_date=sell_time.date(),
                setup=position.setup,
                require_adjustment=True,
            )
            trade.save()
            # clear position
            position.delete()
            # clear manual request if exist
            if manual_request:
                manual_request.delete()
        else:
            utils.print_trading_log(
                "⚠️  Invalid swing sell order response: {}".format(order_response))

    def get_position(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        positions = webullsdk.get_positions()
        if positions == None:
            return None
        ticker_position = None
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                ticker_position = position
                break
        return ticker_position

    # clear unsold positions
    def clear_positions(self):
        iteration = 0
        while len(self.trading_tracker.get_tickers()) > 0:
            for symbol in self.trading_tracker.get_tickers():
                ticker = self.trading_tracker.get_ticker(symbol)
                self.clear_position(ticker)
            # update order
            self.order_tracker.update_orders()
            iteration += 1
            if iteration >= config.CLEAR_POSITION_ITERATIONS:
                break
        # may still have left tickers
        for symbol in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(symbol)
            position_obj = ticker.get_position_obj()
            if position_obj:
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                # remove from monitor
                self.trading_tracker.stop_tracking(ticker)
                utils.print_trading_log(
                    "Failed to clear position <{}>!".format(symbol))
                # send message
                utils.notify_message(
                    "Failed to clear position <{}>, add day position object.".format(symbol))

    def clear_position(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()

        if ticker.is_pending_buy():
            self.check_buy_order_filled(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_filled(ticker, retry_limit=10)
            return

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # remove from monitor
            self.trading_tracker.stop_tracking(ticker)
            return

        sell_price = self.get_sell_price(ticker)
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=sell_price,
            quant=holding_quantity)
        utils.print_trading_log("🔴 Submit clear position order <{}>, quant: {}, limit price: {}".format(
            symbol, holding_quantity, sell_price))
        self.start_tracking_pending_sell_order(
            ticker, order_response, "Clear position.")

    def get_buy_order_limit(self, ticker: TrackingTicker) -> float:
        if self.is_regular_market_hour():
            return self.order_amount_limit
        return self.extended_order_amount_limit

    def get_buy_price(self, ticker: TrackingTicker) -> float:
        ticker_id = ticker.get_id()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        utils.print_level2_log(quote)
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        bid_price = webullsdk.get_bid_price_from_quote(quote) or 0.0
        buy_price = last_price
        if bid_price > last_price:
            ask_price = webullsdk.get_ask_price_from_quote(quote)
            if ask_price:
                buy_price = round((ask_price + bid_price) / 2, 2)
            else:
                buy_price = bid_price + 0.1
        # return min(ask_price, round(last_price * 1.01, 2))
        return buy_price

    def get_buy_price2(self, ticker: TrackingTicker) -> float:
        ticker_id = ticker.get_id()
        symbol = ticker.get_symbol()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        utils.print_level2_log(quote)
        # bid_price = webullsdk.get_bid_price_from_quote(quote)
        # bid_volume = webullsdk.get_bid_volume_from_quote(quote)
        # if ask_price == None or bid_price == None:
        #     return None
        # buy_price = min(bid_price + 0.1, round((ask_price + bid_price) / 2, 2))
        # # buy_price = min(ask_price, round(bid_price * config.BUY_BID_PRICE_RATIO, 2))
        # return buy_price
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        if not ask_price:
            utils.print_trading_log(f"<{symbol}> ask price not existed!")
            utils.print_trading_log(json.dumps(quote))
        return ask_price

    def get_sell_price(self, ticker: TrackingTicker) -> float:
        ticker_id = ticker.get_id()
        symbol = ticker.get_symbol()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        utils.print_level2_log(quote)
        # ask_price = webullsdk.get_ask_price_from_quote(quote)
        # if ask_price == None or bid_price == None:
        #     return None
        # sell_price = max(
        #     ask_price - 0.1, round((ask_price + bid_price) / 2, 2))
        # return sell_price
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        bid_price = webullsdk.get_bid_price_from_quote(quote)
        if not bid_price:
            utils.print_trading_log(f"<{symbol}> bid price not existed!")
            utils.print_trading_log(json.dumps(quote))
        return bid_price or last_price

    def get_sell_price2(self, position: dict) -> float:
        return float(position['lastPrice'])

    def get_stop_loss_price(self, buy_price: float, bars: pd.DataFrame) -> float:
        return 0.0

    def get_scale_stop_loss_price(self, buy_price: float, bars: pd.DataFrame) -> float:
        return 0.0

    def get_buy_dip_loss_price(self, buy_price: float, bars: pd.DataFrame) -> float:
        return 0.0
