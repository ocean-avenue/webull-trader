# -*- coding: utf-8 -*-

# Base trading class

from datetime import datetime
from django.utils import timezone
from typing import Optional
from sdk import webullsdk, fmpsdk
from common import utils, db, sms, constants, exceptions
from common.enums import ActionType, SetupType, TradingHourType
from logger import trading_logger
from trading.tracker.trading_tracker import TradingTracker
from trading.tracker.order_tracker import OrderTracker
from webull_trader.models import ManualTradeRequest, SwingPosition, SwingTrade, WebullOrder


class StrategyBase:

    import pandas as pd
    from common.enums import SetupType, TradingHourType
    from trading.tracker.trading_tracker import TrackingTicker

    ORDER_RETRY_LIMIT = 30

    def __init__(self, paper: bool = True, trading_hour: TradingHourType = TradingHourType.REGULAR):
        # init strategy variables
        self.paper: bool = paper
        self.trading_end: bool = False
        self.trading_hour: TradingHourType = trading_hour
        self.trading_tracker: TradingTracker = TradingTracker()
        self.order_tracker: OrderTracker = OrderTracker(paper=self.paper)

    def begin(self):
        pass

    def update(self):
        pass

    def end(self):
        pass

    def final(self):
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
        trading_logger.log(
            "Buy order limit: {}".format(self.order_amount_limit))

        self.extended_order_amount_limit: float = extended_order_amount_limit
        trading_logger.log("Buy order limit (extended hour): {}".format(
            self.extended_order_amount_limit))

        self.target_profit_ratio: float = target_profit_ratio
        trading_logger.log("Target profit rate: {}%".format(
            round(self.target_profit_ratio * 100, 2)))

        self.stop_loss_ratio: float = stop_loss_ratio
        trading_logger.log("Stop loss rate: {}%".format(
            round(self.stop_loss_ratio * 100, 2)))

        self.day_free_float_limit_in_million: float = day_free_float_limit_in_million
        trading_logger.log("Day trading max free float (million): {}".format(
            self.day_free_float_limit_in_million))

        self.day_turnover_rate_limit_percentage: float = day_turnover_rate_limit_percentage
        trading_logger.log("Day trading min turnover rate: {}%".format(
            self.day_turnover_rate_limit_percentage))

        self.day_sectors_limit: str = day_sectors_limit
        trading_logger.log("Day trading sectors limit: {}".format(
            self.day_sectors_limit))

        self.swing_position_amount_limit: float = swing_position_amount_limit
        trading_logger.log("Swing position amount limit: {}".format(
            self.swing_position_amount_limit))

        self.day_trade_usable_cash_threshold: float = day_trade_usable_cash_threshold
        trading_logger.log("Usable cash threshold for day trade: {}".format(
            self.day_trade_usable_cash_threshold))

    def update_orders(self):
        # update order tracker
        self.order_tracker.update_orders()

    def update_account(self):
        account_data = webullsdk.get_account()
        db.save_webull_account(account_data, paper=self.paper)

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
        tracking_stat = self.trading_tracker.get_stat(symbol)
        # fetch data if not cached
        if day_free_float_limit_in_million > 0 or day_turnover_rate_limit_percentage > 0:
            if tracking_stat.get_free_float() == None or tracking_stat.get_turnover_rate() == None:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                tracking_stat.set_free_float(
                    utils.get_attr_to_float_or_none(quote, "outstandingShares"))
                tracking_stat.set_turnover_rate(
                    utils.get_attr_to_float_or_none(quote, "turnoverRate"))
        free_float_check = True
        if day_free_float_limit_in_million > 0:
            if tracking_stat.get_free_float() == None or \
                    tracking_stat.get_free_float() > day_free_float_limit_in_million * constants.ONE_MILLION:
                free_float_check = False
        turnover_rate_check = True
        if day_turnover_rate_limit_percentage > 0:
            if tracking_stat.get_turnover_rate() == None or \
                    tracking_stat.get_turnover_rate() * constants.ONE_HUNDRED < day_turnover_rate_limit_percentage:
                turnover_rate_check = False
        sectors_check = True
        day_sectors_limit = settings.day_sectors_limit
        if len(day_sectors_limit) > 0:
            # fetch sector if not cached
            if tracking_stat.get_sector() == None:
                profile = fmpsdk.get_profile(symbol)
                if profile and "sector" in profile:
                    tracking_stat.set_sector(profile["sector"])
            sectors_limit = day_sectors_limit.split(",")
            if tracking_stat.get_sector() == None or tracking_stat.get_sector() not in sectors_limit:
                sectors_check = False

        return (free_float_check or turnover_rate_check) and sectors_check

    # submit buy market order, only use for swing trade
    def submit_buy_market_order(self, symbol: str, position: Optional[SwingPosition], unit_weight: int, last_price: float, reason: str):
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        # buy swing position amount
        buy_position_amount = self.get_buy_order_limit(unit_weight)
        if usable_cash <= buy_position_amount:
            trading_logger.log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_quant = (int)(buy_position_amount / last_price)
        # make sure usable cash is enough
        if buy_quant > 0 and (usable_cash - buy_position_amount) > self.day_trade_usable_cash_threshold:
            ticker_id = webullsdk.get_ticker(symbol)
            # submit market buy order
            order_response = webullsdk.buy_market_order(
                ticker_id=ticker_id,
                quant=buy_quant)
            order_id = utils.get_order_id_from_response(
                order_response, paper=self.paper)
            if order_id:
                trading_logger.log(
                    f"🟢 Submit buy order <{symbol}> for {reason}, quant: {buy_quant}, latest price: {last_price}")
                # add/update swing position, always assume market order filled
                self.upsert_pending_swing_position(
                    symbol=symbol,
                    order_id=order_id,
                    position=position,
                    cost=last_price,
                    quant=buy_quant,
                    buy_time=timezone.now(),
                    setup=self.get_setup())
            else:
                trading_logger.log(
                    f"⚠️  Invalid buy order response: {order_response}")
        else:
            if buy_quant == 0:
                trading_logger.log(
                    "Order amount limit not enough for to buy <{}>, price: {}".format(symbol, last_price))
            elif (usable_cash - buy_position_amount) <= self.day_trade_usable_cash_threshold:
                trading_logger.log(
                    "Not enough cash for day trade threshold, skip <{}>, price: {}".format(symbol, last_price))

    # submit buy market order, only use for swing trade
    def submit_sell_market_order(self, symbol: str, position: SwingPosition, last_price: float, reason: str, manual_request: Optional[ManualTradeRequest] = None):
        ticker_id = webullsdk.get_ticker(symbol)
        # submit market sell order
        order_response = webullsdk.sell_market_order(
            ticker_id=ticker_id,
            quant=position.quantity)
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            trading_logger.log(
                f"🔴 Submit sell order <{symbol}> for {reason}, quant: {position.quantity}, latest price: ${last_price}")
            # add swing trade
            self.add_pending_swing_trade(
                symbol=symbol,
                order_id=order_id,
                position=position,
                price=last_price,
                sell_time=timezone.now(),
                manual_request=manual_request)
        else:
            trading_logger.log(
                f"⚠️  Invalid buy order response: {order_response}")
            # send message
            sms.notify_message(
                f"Failed to sell <{symbol}> swing position, please check now!")

    # submit buy limit order, only use for day trade
    def submit_buy_limit_order(self, ticker: TrackingTicker, note: str = "Entry point."):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            trading_logger.log(
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
            order_id = utils.get_order_id_from_response(
                order_response, paper=self.paper)
            if order_id:
                trading_logger.log(
                    f"🟢 Submit buy order {order_id}, ticker: <{symbol}>, quant: {buy_quant}, limit price: {buy_price}")
                # tracking pending buy order
                self.start_tracking_pending_buy_order(
                    ticker, order_id, entry_note=note)
            else:
                trading_logger.log(
                    f"⚠️  Invalid buy order response: {order_response}")
        else:
            trading_logger.log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

    def modify_buy_limit_order(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = ticker.get_pending_order_id()
        usable_cash = webullsdk.get_usable_cash()
        db.save_webull_min_usable_cash(usable_cash)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            trading_logger.log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_price = self.get_buy_price(ticker)
        if not buy_price:
            return
        buy_quant = (int)(buy_position_amount / buy_price)
        order_response = webullsdk.modify_buy_limit_order(
            ticker_id=ticker_id,
            order_id=order_id,
            price=buy_price,
            quant=buy_quant)
        trading_logger.log(
            f"🟢 Modify buy order {order_id}, ticker: <{symbol}>, quant: {buy_quant}, limit price: {buy_price}")
        trading_logger.log(
            f"⚠️  Modify buy order response: {order_response}")

    # submit sell limit order, only use for day trade
    def submit_sell_limit_order(self, ticker: TrackingTicker, note: str = "Exit point."):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        holding_quantity = ticker.get_positions()
        sell_price = self.get_sell_price(ticker)
        if not sell_price:
            return
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=sell_price,
            quant=holding_quantity)
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            trading_logger.log(
                f"🔴 Submit sell order {order_id}, ticker: <{symbol}>, quant: {holding_quantity}, limit price: {sell_price}")
            # tracking pending sell order
            self.start_tracking_pending_sell_order(
                ticker, order_id, exit_note=note)
        else:
            trading_logger.log(
                f"⚠️  Invalid sell order response: {order_response}")

    def modify_sell_limit_order(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = ticker.get_pending_order_id()
        holding_quantity = ticker.get_positions()
        sell_price = self.get_sell_price(ticker)
        order_response = webullsdk.modify_sell_limit_order(
            ticker_id=ticker_id,
            order_id=order_id,
            price=sell_price,
            quant=holding_quantity)
        trading_logger.log(
            f"🔴 Modify sell order {order_id}, ticker: <{symbol}>, quant: {holding_quantity}, limit price: {sell_price}")
        trading_logger.log(
            f"⚠️  Modify sell order response: {order_response}")

    def check_pending_order_done(self, ticker: TrackingTicker):

        if ticker.is_pending_buy():
            self.check_buy_order_done(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_done(ticker)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

    def _on_buy_order_filled(self, ticker: TrackingTicker, order: WebullOrder,
                             stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIAL_FILLED:
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
            ticker.inc_positions(order.filled_quantity)
            ticker.inc_units()
            ticker.reset_resubmit_order_count()
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)

    def check_buy_order_done(self, ticker: TrackingTicker,
                             stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            trading_logger.log(
                f"Buy order {order_id} - <{symbol}> {webullsdk.ORDER_STATUS_NOT_FOUND}")
            if ticker.is_order_timeout():
                # cancel in case we did not catch the order
                webullsdk.cancel_order(order_id)
                # stop tracking buy order
                self.stop_tracking_pending_buy_order(ticker, order_id)
            return
        trading_logger.log(f"Buy order {order_id} - <{symbol}> {order.status}")
        # filled or partially filled
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIAL_FILLED:
            self._on_buy_order_filled(
                ticker, order, stop_tracking_ticker_after_order_filled)
            trading_logger.log(f"Filled price: ${order.avg_price}")
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout() or self.trading_end:
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Buy order timeout, canceled!")
                else:
                    trading_logger.log(
                        f"Failed to cancel timeout buy order {order_id} - <{symbol}>!")
            # else:
            #     # modify order price to make it easier to buy
            #     self.modify_buy_limit_order(ticker)
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking buy order
            self.stop_tracking_pending_buy_order(ticker, order_id)
        # unknown status
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}', {order_id} - <{symbol}>!")

    def _on_sell_order_filled(self, ticker: TrackingTicker, order: WebullOrder,
                              stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
        if order.status == webullsdk.ORDER_STATUS_FILLED:
            position_obj = ticker.get_position_obj()
            # add trade object
            trade = db.add_day_trade(
                symbol=symbol,
                ticker_id=ticker_id,
                position=position_obj,
                order_id=order_id,
                sell_price=order.avg_price,
                sell_time=order.filled_time,
            )
            # remove position object
            position_obj.delete()
            ticker.reset_positions()
            ticker.reset_resubmit_order_count()
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # stop tracking ticker
            if stop_tracking_ticker_after_order_filled:
                self.trading_tracker.stop_tracking(ticker)
            # update trading stats
            tracking_stat = self.trading_tracker.get_stat(symbol)
            tracking_stat.update_by_trade(trade)
        # partially filled
        elif order.status == webullsdk.ORDER_STATUS_PARTIAL_FILLED:
            position_obj = ticker.get_position_obj()
            # update position object
            position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
            position_obj.require_adjustment = True
            position_obj.save()
            # update tracking ticker
            ticker.dec_positions(order.filled_quantity)
            ticker.reset_resubmit_order_count()
            # stop tracking sell order
            self.stop_tracking_pending_sell_order(ticker, order_id)
            # continue sell reset positions
            trading_logger.log(
                f"Continue sell rest <{symbol}> positions, quant: {ticker.get_positions()}")
            self.submit_sell_limit_order(ticker, note="Sell rest positions.")
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}', {order_id} - <{symbol}>!")
        # update account status
        self.update_account()

    def _on_sell_order_failed(self, ticker: TrackingTicker, order_status: str, stop_tracking_ticker_after_order_done: bool = True):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        if order_status in [webullsdk.ORDER_STATUS_FAILED, webullsdk.ORDER_STATUS_CANCELED, webullsdk.ORDER_STATUS_NOT_FOUND]:
            resubmit_count = ticker.get_resubmit_order_count()
            self.stop_tracking_pending_sell_order(ticker, order_id)
            if resubmit_count < self.ORDER_RETRY_LIMIT and not self.trading_end:
                # retry sell order
                trading_logger.log(
                    f"Resubmitting sell order <{symbol}>...")
                self.submit_sell_limit_order(
                    ticker, note=f"Resubmit sell order ({resubmit_count}).")
                # increment resubmit order count
                ticker.inc_resubmit_order_count()
            else:
                position_obj = ticker.get_position_obj()
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                trading_logger.log(
                    "Failed to sell position <{}>!".format(symbol))
                # send message
                sms.notify_message(
                    f"Failed to sell <{symbol}> position, please check now!")
                # stop tracking ticker
                if stop_tracking_ticker_after_order_done:
                    self.trading_tracker.stop_tracking(ticker)
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order_status}' for order: {order_id}!")

    def check_sell_order_done(self, ticker: TrackingTicker,
                              stop_tracking_ticker_after_order_filled: bool = False):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if order == None:
            trading_logger.log(
                f"Sell order {order_id} - <{symbol}> {webullsdk.ORDER_STATUS_NOT_FOUND}")
            if ticker.is_order_timeout():
                # cancel in case we did not catch the order
                webullsdk.cancel_order(order_id)
                self._on_sell_order_failed(
                    ticker, webullsdk.ORDER_STATUS_NOT_FOUND, stop_tracking_ticker_after_order_filled)
            return
        trading_logger.log(
            f"Sell order {order_id} - <{symbol}> {order.status}")
        # filled or partially filled
        if order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIAL_FILLED:
            self._on_sell_order_filled(
                ticker, order, stop_tracking_ticker_after_order_filled)
            trading_logger.log(f"Filled price: ${order.avg_price}")
        # pending or working
        elif order.status == webullsdk.ORDER_STATUS_PENDING or order.status == webullsdk.ORDER_STATUS_WORKING:
            if ticker.is_order_timeout():
                # timeout, cancel order
                if webullsdk.cancel_order(order_id):
                    # start tracking cancel order
                    self.start_tracking_pending_cancel_order(
                        ticker, order_id, cancel_note="Sell order timeout, canceled!")
                else:
                    trading_logger.log(
                        f"Failed to cancel timeout sell order {order_id} - <{symbol}>!")
            # else:
            #     # modify order price to make it easier to sell
            #     self.modify_sell_limit_order(ticker)
        # failed or canceled
        elif order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            self._on_sell_order_failed(
                ticker, order.status, stop_tracking_ticker_after_order_filled)
        # unknown status
        else:
            raise exceptions.WebullOrderStatusError(
                f"Unknown order status '{order.status}', {order_id} - <{symbol}>!")

    def check_cancel_order_done(self, ticker: TrackingTicker,
                                stop_tracking_ticker_after_order_canceled: bool = False):
        symbol = ticker.get_symbol()
        order_id = ticker.get_pending_order_id()
        order = self.order_tracker.get_order(order_id)
        if not order:
            trading_logger.log(
                f"Cancel order {order_id} - <{symbol}> {webullsdk.ORDER_STATUS_NOT_FOUND}")
            raise exceptions.WebullOrderNotFoundError()
        trading_logger.log(
            f"Cancel order {order_id} - <{symbol}> {order.status}")
        # failed or canceled
        if order.status == webullsdk.ORDER_STATUS_FAILED or order.status == webullsdk.ORDER_STATUS_CANCELED:
            # stop tracking cancel order
            self.stop_tracking_pending_cancel_order(ticker, order_id)
            # buy order
            if order.action == ActionType.BUY:
                if stop_tracking_ticker_after_order_canceled:
                    self.trading_tracker.stop_tracking(ticker)
            # sell order
            if order.action == ActionType.SELL:
                self._on_sell_order_failed(
                    ticker, order.status, stop_tracking_ticker_after_order_canceled)
        elif order.status == webullsdk.ORDER_STATUS_FILLED or order.status == webullsdk.ORDER_STATUS_PARTIAL_FILLED:
            # buy order
            if order.action == ActionType.BUY:
                self._on_buy_order_filled(ticker, order)
            # sell order
            if order.action == ActionType.SELL:
                self._on_sell_order_filled(ticker, order)
        elif ticker.is_order_timeout():
            if not utils.is_paper_trading():
                sms.notify_message(
                    f"Failed to cancel <{symbol}> order: {order_id}, please check now!")
            raise exceptions.WebullOrderTimeoutError(
                f"Error cancel order timeout '{order.status}', {order_id} - <{symbol}>")

    def start_tracking_pending_buy_order(self, ticker: TrackingTicker, order_id: str, entry_note: str = ""):
        ticker.reset_pending_order()
        # mark pending buy
        ticker.set_pending_buy(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id=order_id,
            setup=self.get_setup(),
            note=entry_note)

    def stop_tracking_pending_buy_order(self, ticker: TrackingTicker, order_id: str):
        if ticker.get_pending_order_id() == order_id:
            ticker.reset_pending_order()
        ticker.set_last_buy_time(datetime.now())
        self.order_tracker.stop_tracking(order_id)

    def start_tracking_pending_sell_order(self, ticker: TrackingTicker, order_id: str, exit_note: str = ""):
        ticker.reset_pending_order()
        # mark pending sell
        ticker.set_pending_sell(True)
        ticker.set_pending_order_id(order_id)
        ticker.set_pending_order_time(datetime.now())
        # tracking order
        self.order_tracker.start_tracking(
            order_id=order_id,
            setup=self.get_setup(),
            note=exit_note)

    def stop_tracking_pending_sell_order(self, ticker: TrackingTicker, order_id: str):
        if ticker.get_pending_order_id() == order_id:
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
        if ticker.get_pending_order_id() == order_id:
            ticker.reset_pending_order()
        self.order_tracker.stop_tracking(order_id)

    def upsert_pending_swing_position(self, symbol: str, order_id: str, position: Optional[SwingPosition],
                                      cost: float, quant: int, buy_time: datetime, setup: SetupType):
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
            position.order_ids = f"{position.order_ids},{order_id}"
            position.total_cost = position.total_cost + cost * quant
            position.quantity = position.quantity + quant
            position.units = position.units + 1
            # temp add unit, stop loss price
            position.add_unit_price = constants.MAX_SECURITY_PRICE
            position.stop_loss_price = 0
            position.require_adjustment = True
        position.save()

    def add_pending_swing_trade(self, symbol: str, order_id: str, position: SwingPosition,
                                price: float, sell_time: datetime, manual_request: Optional[ManualTradeRequest] = None):
        order_ids = f"{position.order_ids},{order_id}"
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

    # clear all positions
    def clear_positions(self):
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            self.clear_position(ticker)

    def clear_position(self, ticker: TrackingTicker):

        if ticker.is_pending_buy():
            self.check_buy_order_done(ticker)
            return

        if ticker.is_pending_sell():
            self.check_sell_order_done(ticker)
            return

        if ticker.is_pending_cancel():
            self.check_cancel_order_done(ticker)
            return

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)
            return

        self.submit_sell_limit_order(ticker, note="Clear position.")

    def track_rest_positions(self):
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            symbol = ticker.get_symbol()
            position_obj = ticker.get_position_obj()
            if position_obj:
                # update setup
                position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                position_obj.save()
                # send message
                sms.notify_message(
                    f"Failed to clear <{symbol}> position, please check now!")
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)

    def get_buy_order_limit(self, ticker: TrackingTicker) -> float:
        if self.is_regular_market_hour():
            return self.order_amount_limit
        return self.extended_order_amount_limit

    def get_buy_price(self, ticker: TrackingTicker) -> Optional[float]:
        ticker_id = ticker.get_id()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        trading_logger.log_level2(quote)
        close_price = utils.get_attr_to_float_or_none(quote, 'close')
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        last_price = last_price or close_price
        bid_price = webullsdk.get_bid_price_from_quote(quote) or last_price
        ask_price = webullsdk.get_ask_price_from_quote(quote) or last_price
        if not bid_price or not ask_price:
            trading_logger.log(
                f"<{ticker.get_symbol()}> buy price None, quote: {quote}")
            return None
        buy_price = round((ask_price + bid_price) / 2 + 0.005, 2)
        # return min(ask_price, round(last_price * 1.01, 2))
        return buy_price

    def get_sell_price(self, ticker: TrackingTicker) -> Optional[float]:
        ticker_id = ticker.get_id()
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        trading_logger.log_level2(quote)
        # ask_price = webullsdk.get_ask_price_from_quote(quote)
        # if ask_price == None or bid_price == None:
        #     return None
        # sell_price = max(
        #     ask_price - 0.1, round((ask_price + bid_price) / 2, 2))
        # return sell_price
        close_price = utils.get_attr_to_float_or_none(quote, 'close')
        if self.is_regular_market_hour():
            last_price = utils.get_attr_to_float_or_none(quote, 'close')
        else:
            last_price = utils.get_attr_to_float_or_none(quote, 'pPrice')
        last_price = last_price or close_price
        bid_price = webullsdk.get_bid_price_from_quote(quote) or last_price
        ask_price = webullsdk.get_ask_price_from_quote(quote) or last_price
        if not bid_price or not ask_price:
            trading_logger.log(
                f"<{ticker.get_symbol()}> sell price None, quote: {quote}")
            return None
        sell_price = round((ask_price + bid_price) / 2 - 0.005, 2)
        return sell_price

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_scale_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_dip_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0
