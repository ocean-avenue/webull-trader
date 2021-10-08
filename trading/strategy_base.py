# -*- coding: utf-8 -*-

# Base trading class

import time
from datetime import datetime, timedelta, date
from django.utils import timezone
from webull_trader.models import DayPosition, SwingPosition, SwingTrade, TradingSettings
from webull_trader.enums import SetupType, TradingHourType
from sdk import webullsdk, fmpsdk
from scripts import utils, config


class StrategyBase:

    def __init__(self, paper=True, trading_hour=TradingHourType.REGULAR):
        self.paper = paper
        self.trading_hour = trading_hour
        self.trading_end = False
        # init trading variables
        self.tracking_tickers = {}
        self.tracking_stats = {}
        # may have error short sell due to latency
        self.error_short_tickers = {}
        # sometime system may not cancel order correctly
        self.canceled_orders = {}
        # for swing trade
        self.trading_watchlist = []
        # init trading logs
        utils.TRADING_LOGS = []

    def on_begin(self):
        pass

    def on_update(self):
        pass

    def on_end(self):
        pass

    def get_tag(self):
        return ""

    # load settings
    def load_settings(self,
                      order_amount_limit,
                      extended_order_amount_limit,
                      target_profit_ratio,
                      stop_loss_ratio,
                      day_free_float_limit_in_million,
                      day_turnover_rate_limit_percentage,
                      day_sectors_limit,
                      swing_position_amount_limit,
                      day_trade_usable_cash_threshold):

        self.order_amount_limit = order_amount_limit
        utils.print_trading_log(
            "Buy order limit: {}".format(self.order_amount_limit))

        self.extended_order_amount_limit = extended_order_amount_limit
        utils.print_trading_log("Buy order limit (extended hour): {}".format(
            self.extended_order_amount_limit))

        self.target_profit_ratio = target_profit_ratio
        utils.print_trading_log("Target profit rate: {}%".format(
            round(self.target_profit_ratio * 100, 2)))

        self.stop_loss_ratio = stop_loss_ratio
        utils.print_trading_log("Stop loss rate: {}%".format(
            round(self.stop_loss_ratio * 100, 2)))

        self.day_free_float_limit_in_million = day_free_float_limit_in_million
        utils.print_trading_log("Day trading max free float (million): {}".format(
            self.day_free_float_limit_in_million))

        self.day_turnover_rate_limit_percentage = day_turnover_rate_limit_percentage
        utils.print_trading_log("Day trading min turnover rate: {}%".format(
            self.day_turnover_rate_limit_percentage))

        self.day_sectors_limit = day_sectors_limit
        utils.print_trading_log("Day trading sectors limit: {}".format(
            self.day_sectors_limit))

        self.swing_position_amount_limit = swing_position_amount_limit
        utils.print_trading_log("Swing position amount limit: {}".format(
            self.swing_position_amount_limit))

        self.day_trade_usable_cash_threshold = day_trade_usable_cash_threshold
        utils.print_trading_log("Usable cash threshold for day trade: {}".format(
            self.day_trade_usable_cash_threshold))

        return True

    def save_logs(self):
        # save trading logs
        utils.save_trading_log(self.get_tag(), self.trading_hour, date.today())

    def build_tracking_ticker(self, symbol, ticker_id, prev_close=None, prev_high=None):
        # init tracking stats if not
        if symbol not in self.tracking_stats:
            self.tracking_stats[symbol] = {
                "trades": 0,
                "win_trades": 0,
                "lose_trades": 0,
                "sector": None,
                "free_float": None,
                "turnover_rate": None,
                "continue_lose_trades": 0,
                "last_high_price": None,
                "last_trade_time": None,
            }
        # init tracking tocker
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            "pending_buy": False,
            "pending_sell": False,
            "pending_order_id": None,
            "pending_order_time": None,
            "last_profit_loss_rate": None,
            "last_buy_time": None,
            "last_sell_time": None,
            "positions": 0,
            "start_time": datetime.now(),
            "target_profit": None,
            "stop_loss": None,
            # paper trade do not have stop trailing order, this value keep track of max P&L
            "max_profit_loss_rate": 0,
            "exit_note": None,
            "prev_close": prev_close,
            "prev_high": prev_high,
            "resubmit_count": 0,
            "initial_cost": None,
            "exit_period": None,
            "position_obj": None,
        }

    def build_error_short_ticker(self, symbol, ticker_id):
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            # pending buy back order id
            "pending_order_id": None,
            # pending buy back order time
            "pending_order_time": None,
        }

    def is_regular_market_hour(self):
        return self.trading_hour == TradingHourType.REGULAR

    def is_pre_market_hour(self):
        return self.trading_hour == TradingHourType.BEFORE_MARKET_OPEN

    def is_after_market_hour(self):
        return self.trading_hour == TradingHourType.AFTER_MARKET_CLOSE

    def is_extended_market_hour(self):
        return self.is_pre_market_hour() or self.is_after_market_hour()

    def check_can_trade_ticker(self, ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        settings = TradingSettings.objects.first()
        if not settings:
            return True
        day_free_float_limit_in_million = settings.day_free_float_limit_in_million
        day_turnover_rate_limit_percentage = settings.day_turnover_rate_limit_percentage
        # fetch data if not cached
        if day_free_float_limit_in_million > 0 or day_turnover_rate_limit_percentage > 0:
            if self.tracking_stats[symbol]["free_float"] == None or self.tracking_stats[symbol]["turnover_rate"] == None:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                self.tracking_stats[symbol]["free_float"] = utils.get_attr_to_float_or_none(
                    quote, "outstandingShares")
                self.tracking_stats[symbol]["turnover_rate"] = utils.get_attr_to_float_or_none(
                    quote, "turnoverRate")
        free_float_check = True
        if day_free_float_limit_in_million > 0:
            if self.tracking_stats[symbol]["free_float"] == None or \
                    self.tracking_stats[symbol]["free_float"] > day_free_float_limit_in_million * config.ONE_MILLION:
                free_float_check = False
        turnover_rate_check = True
        if day_turnover_rate_limit_percentage > 0:
            if self.tracking_stats[symbol]["turnover_rate"] == None or \
                    self.tracking_stats[symbol]["turnover_rate"] * config.ONE_HUNDRED < day_turnover_rate_limit_percentage:
                turnover_rate_check = False
        sectors_check = True
        day_sectors_limit = settings.day_sectors_limit
        if len(day_sectors_limit) > 0:
            # fetch sector if not cached
            if self.tracking_stats[symbol]["sector"] == None:
                profile = fmpsdk.get_profile(symbol)
                if profile and "sector" in profile:
                    self.tracking_stats[symbol]["sector"] = profile["sector"]
            sectors_limit = day_sectors_limit.split(",")
            if self.tracking_stats[symbol]["sector"] == None or self.tracking_stats[symbol]["sector"] not in sectors_limit:
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
                    if webullsdk.cancel_order(ticker['pending_order_id']):
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
            if symbol in self.tracking_tickers:
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
            ticker = self.build_tracking_ticker(symbol, ticker_id)
            ticker['positions'] = int(position['position'])
            ticker['last_buy_time'] = datetime.now()
            ticker['initial_cost'] = float(position['costPrice'])
            order_id = utils.get_attr_to_num(self.canceled_orders, symbol)
            # save order note
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
            ticker['position_obj'] = position_obj
            # recover tracking
            self.tracking_tickers[symbol] = ticker

    def check_buy_order_filled(self, ticker, resubmit=False, resubmit_count=10, stop_tracking=False, target_units=4):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        order_id = ticker['pending_order_id']
        utils.print_trading_log(
            "Checking buy order <{}> filled...".format(symbol))
        positions = webullsdk.get_positions()
        if positions == None:
            return False
        order_filled = False
        for position in positions:
            if position['ticker']['symbol'] != symbol:
                continue
            quantity = int(position['position'])
            cost = float(position['costPrice'])
            position_obj = ticker['position_obj']
            stop_loss = ticker['stop_loss'] or 0.0
            if position_obj:
                if quantity > position_obj.quantity:
                    # order filled
                    order_filled = True
                    # update position obj
                    position_obj.order_ids = "{},{}".format(
                        position_obj.order_ids, order_id)
                    position_obj.quantity = quantity
                    position_obj.total_cost = round(quantity * cost, 2)
                    position_obj.units = position_obj.units + 1
                    position_obj.save()
            else:
                # order filled
                order_filled = True
                # add position obj
                position_obj = utils.add_day_position(
                    symbol=symbol,
                    ticker_id=ticker_id,
                    order_id=order_id,
                    setup=self.get_setup(),
                    cost=cost,
                    quant=quantity,
                    buy_time=timezone.now(),
                    stop_loss_price=stop_loss,
                    target_units=target_units,
                )
                # set initial cost
                self.tracking_tickers[symbol]['initial_cost'] = cost
            if order_filled:
                entry_note = "Entry point."
                resubmit_count = ticker['resubmit_count']
                if resubmit_count > 0:
                    entry_note = "{} {}".format(
                        entry_note, "Resubmit buy order ({}).".format(resubmit_count))
                # save order note
                utils.save_webull_order_note(
                    order_id, setup=self.get_setup(), note=entry_note)
                # update tracking_tickers
                self.tracking_tickers[symbol]['positions'] = quantity
                self.tracking_tickers[symbol]['pending_buy'] = False
                self.tracking_tickers[symbol]['pending_order_id'] = None
                self.tracking_tickers[symbol]['pending_order_time'] = None
                self.tracking_tickers[symbol]['resubmit_count'] = 0
                self.tracking_tickers[symbol]['last_buy_time'] = datetime.now(
                )
                self.tracking_tickers[symbol]['position_obj'] = position_obj
                # print log
                utils.print_trading_log(
                    "Buy order <{}> filled, cost: {}".format(symbol, cost))
                # remove from monitor
                if stop_tracking:
                    del self.tracking_tickers[symbol]
                # exit loop
                break
        if not order_filled:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=config.PENDING_ORDER_TIMEOUT_IN_SEC) or self.trading_end:
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(ticker['pending_order_id'], setup=self.get_setup(
                    ), note="Buy order timeout, canceled!")
                    utils.print_trading_log(
                        "Buy order <{}> timeout, canceled!".format(symbol))
                    # resubmit buy order
                    if resubmit and self.tracking_tickers[symbol]['resubmit_count'] <= resubmit_count:
                        quote = webullsdk.get_quote(ticker_id=ticker_id)
                        ask_price = webullsdk.get_ask_price_from_quote(quote)
                        if ask_price == None:
                            return False
                        usable_cash = webullsdk.get_usable_cash()
                        utils.save_webull_min_usable_cash(usable_cash)
                        buy_position_amount = self.get_buy_order_limit(ticker)
                        if usable_cash <= buy_position_amount:
                            utils.print_trading_log(
                                "Not enough cash to buy <{}> again, ask price: {}!".format(symbol, ask_price))
                            return False
                        buy_quant = (int)(buy_position_amount / ask_price)
                        order_response = webullsdk.buy_limit_order(
                            ticker_id=ticker_id,
                            price=ask_price,
                            quant=buy_quant)
                        utils.print_trading_log("Resubmit buy order <{}>, quant: {}, limit price: {}".format(
                            symbol, buy_quant, ask_price))
                        self.update_pending_buy_order(ticker, order_response)
                        self.tracking_tickers[symbol]['resubmit_count'] += 1
                    else:
                        # cache cancel order
                        self.canceled_orders[symbol] = ticker['pending_order_id']
                        # reset tracking_tickers
                        self.tracking_tickers[symbol]['pending_buy'] = False
                        self.tracking_tickers[symbol]['pending_order_id'] = None
                        self.tracking_tickers[symbol]['pending_order_time'] = None
                        self.tracking_tickers[symbol]['resubmit_count'] = 0
                        # remove from monitor
                        if stop_tracking:
                            del self.tracking_tickers[symbol]
                else:
                    utils.print_trading_log(
                        "Failed to cancel timeout buy order <{}>!".format(symbol))

        # check short order
        self.check_error_short_order(positions)

        # check failed to cancel order
        self.check_error_cancel_order(positions)

        return order_filled

    def check_sell_order_filled(self, ticker, resubmit=True, resubmit_count=10, stop_tracking=True):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        order_id = ticker['pending_order_id']
        exit_note = ticker['exit_note']
        utils.print_trading_log(
            "Checking sell order <{}> filled...".format(symbol))
        positions = webullsdk.get_positions()
        if positions == None:
            return False
        order_filled = True
        holding_quantity = 0
        for position in positions:
            if position['ticker']['symbol'] != symbol:
                continue
            holding_quantity = int(position['position'])
            # make sure position is positive
            if holding_quantity > 0:
                order_filled = False
                break
        if order_filled:
            # check if have any exit note
            if exit_note:
                # save order note
                utils.save_webull_order_note(
                    order_id, setup=self.get_setup(), note=exit_note)
            # add trade object
            position_obj = ticker['position_obj']
            profit_loss_rate = ticker['last_profit_loss_rate'] or 0.0
            sell_price = round((position_obj.total_cost /
                                position_obj.quantity) * (1+profit_loss_rate), 2)
            utils.add_day_trade(
                symbol=symbol,
                ticker_id=ticker_id,
                position=position_obj,
                order_id=order_id,
                sell_price=sell_price,
                sell_time=timezone.now(),
            )
            # remove position object
            position_obj.delete()
            # update tracking_tickers
            self.tracking_tickers[symbol]['positions'] = 0
            self.tracking_tickers[symbol]['pending_sell'] = False
            self.tracking_tickers[symbol]['pending_order_id'] = None
            self.tracking_tickers[symbol]['pending_order_time'] = None
            self.tracking_tickers[symbol]['last_sell_time'] = datetime.now()
            self.tracking_tickers[symbol]['exit_note'] = None
            self.tracking_tickers[symbol]['resubmit_count'] = 0
            self.tracking_tickers[symbol]['position_obj'] = None
            self.tracking_tickers[symbol]['initial_cost'] = None
            # remove from monitor
            if stop_tracking:
                del self.tracking_tickers[symbol]
            utils.print_trading_log("Sell order <{}> filled".format(symbol))
            # update account status
            account_data = webullsdk.get_account()
            utils.save_webull_account(account_data, paper=self.paper)
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=config.PENDING_ORDER_TIMEOUT_IN_SEC):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(ticker['pending_order_id'], setup=self.get_setup(
                    ), note="Sell order timeout, canceled!")
                    utils.print_trading_log(
                        "Sell order <{}> timeout, canceled!".format(symbol))
                    # resubmit sell order
                    if resubmit and self.tracking_tickers[symbol]['resubmit_count'] <= resubmit_count:
                        quote = webullsdk.get_quote(ticker_id=ticker_id)
                        if quote == None:
                            return False
                        bid_price = webullsdk.get_bid_price_from_quote(quote)
                        if bid_price == None:
                            return False
                        # holding_quantity = ticker['positions']
                        order_response = webullsdk.sell_limit_order(
                            ticker_id=ticker_id,
                            price=bid_price,
                            quant=holding_quantity)
                        utils.print_trading_log("Resubmit sell order <{}>, quant: {}, limit price: {}".format(
                            symbol, holding_quantity, bid_price))
                        self.tracking_tickers[symbol]['resubmit_count'] += 1
                        self.update_pending_sell_order(
                            ticker, order_response, "{} Resubmit sell order ({}).".format(
                                exit_note, self.tracking_tickers[symbol]['resubmit_count']))
                    else:
                        position_obj = ticker['position_obj']
                        # update setup
                        position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
                        position_obj.save()
                        # remove from monitor
                        del self.tracking_tickers[symbol]
                        utils.print_trading_log(
                            "Failed to sell order <{}>!".format(symbol))
                        # send message
                        utils.notify_message(
                            "Failed to sell <{}>, add day position object.".format(symbol))
                else:
                    utils.print_trading_log(
                        "Failed to cancel timeout sell order <{}>!".format(symbol))

        # check short order
        self.check_error_short_order(positions)

        # check failed to cancel order
        self.check_error_cancel_order(positions)

        return order_filled

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

    def update_pending_buy_order(self, ticker, order_response, target_profit=None, stop_loss=None):
        symbol = ticker['symbol']
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            # mark pending buy
            self.tracking_tickers[symbol]['pending_buy'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_id
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            # set target profit
            if target_profit:
                self.tracking_tickers[symbol]['target_profit'] = target_profit
            # set stop loss
            if stop_loss:
                self.tracking_tickers[symbol]['stop_loss'] = stop_loss
        else:
            utils.print_trading_log(
                "⚠️  Invalid buy order response: {}".format(order_response))

    def update_pending_sell_order(self, ticker, order_response, exit_note=""):
        symbol = ticker['symbol']
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            # mark pending sell
            self.tracking_tickers[symbol]['pending_sell'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_id
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            self.tracking_tickers[symbol]['exit_note'] = exit_note
        else:
            utils.print_trading_log(
                "⚠️  Invalid sell order response: {}".format(order_response))

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
                position.add_unit_price = 9999
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

    def get_position(self, ticker):
        symbol = ticker['symbol']
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
        while len(list(self.tracking_tickers)) > 0:
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                self.clear_position(ticker)
            # at least sleep 1 sec
            time.sleep(1)
            iteration += 1
            if iteration >= config.CLEAR_POSITION_ITERATIONS:
                break
        # may still have left tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            position_obj = ticker['position_obj']
            # update setup
            position_obj.setup = SetupType.ERROR_FAILED_TO_SELL
            position_obj.save()
            # remove from monitor
            del self.tracking_tickers[symbol]
            utils.print_trading_log(
                "Failed to clear position <{}>!".format(symbol))
            # send message
            utils.notify_message(
                "Failed to clear position <{}>, add day position object.".format(symbol))

    def clear_position(self, ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker, resubmit_count=10)
            return

        holding_quantity = ticker['positions']
        if holding_quantity == 0:
            # remove from monitor
            del self.tracking_tickers[symbol]
            return

        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return
        bid_price = webullsdk.get_bid_price_from_quote(quote)
        if bid_price == None:
            return
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=bid_price,
            quant=holding_quantity)
        utils.print_trading_log("🔴 Submit clear position order <{}>, quant: {}, limit price: {}".format(
            symbol, holding_quantity, bid_price))
        if utils.get_order_id_from_response(order_response, paper=self.paper):
            self.update_pending_sell_order(
                ticker, order_response, exit_note="Clear position.")
        else:
            utils.print_trading_log(
                "⚠️  Invalid clear position order response: {}".format(order_response))

    def get_setup(self):
        return SetupType.UNKNOWN

    def get_buy_order_limit(self, ticker):
        if self.is_regular_market_hour():
            return self.order_amount_limit
        return self.extended_order_amount_limit

    def get_buy_price(self, ticker):
        ticker_id = ticker['ticker_id']
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return None
        # bid_price = webullsdk.get_bid_price_from_quote(quote)
        # bid_volume = webullsdk.get_bid_volume_from_quote(quote)
        ask_price = webullsdk.get_ask_price_from_quote(quote)
        return ask_price
        # if ask_price == None or bid_price == None:
        #     return None
        # buy_price = min(bid_price + 0.1, round((ask_price + bid_price) / 2, 2))
        # # buy_price = min(ask_price, round(bid_price * config.BUY_BID_PRICE_RATIO, 2))
        # return buy_price

    def get_sell_price(self, ticker):
        ticker_id = ticker['ticker_id']
        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return None
        bid_price = webullsdk.get_bid_price_from_quote(quote)
        return bid_price
        # ask_price = webullsdk.get_ask_price_from_quote(quote)
        # if ask_price == None or bid_price == None:
        #     return None
        # sell_price = max(
        #     ask_price - 0.1, round((ask_price + bid_price) / 2, 2))
        # return sell_price
