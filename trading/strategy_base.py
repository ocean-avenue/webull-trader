# -*- coding: utf-8 -*-

# Base trading class

from datetime import datetime, timedelta
from webull_trader.models import SwingPosition, SwingTrade
from webull_trader.enums import TradingHourType
from sdk import webullsdk
from scripts import utils


class StrategyBase:

    def __init__(self, paper=True):
        self.paper = paper
        self.trading_end = False
        # init trading variables
        self.tracking_tickers = {}
        self.tracking_stats = {}
        # may have error short sell due to latency
        self.error_short_tickers = {}
        self.trading_logs = []
        # for swing trade
        self.trading_symbols = []

    def on_begin(self):
        pass

    def on_update(self):
        pass

    def on_end(self):
        pass

    def get_tag(self):
        return ""

    def get_trading_hour(self):
        now = datetime.now()
        if now.hour < 9 or now.hour == 9 and now.minute < 30:
            return TradingHourType.BEFORE_MARKET_OPEN
        if now.hour >= 16:
            return TradingHourType.AFTER_MARKET_CLOSE
        return TradingHourType.REGULAR

    def print_log(self, text):
        self.trading_logs.append(
            "[{}] {}".format(utils.get_now(), text))
        # output
        print(text)

    # load settings
    def load_settings(self,
                      min_surge_amount,
                      min_surge_volume,
                      min_surge_change_ratio,
                      avg_confirm_volume,
                      order_amount_limit,
                      observe_timeout_in_sec,
                      trade_interval_in_sec,
                      pending_order_timeout_in_sec,
                      holding_order_timeout_in_sec,
                      max_bid_ask_gap_ratio,
                      target_profit_ratio,
                      stop_loss_ratio,
                      blacklist_timeout_in_sec,
                      swing_position_amount_limit,
                      max_prev_day_close_gap_ratio,
                      min_relative_volume,
                      min_earning_gap_ratio,
                      day_trade_usable_cash_threshold):

        self.min_surge_amount = min_surge_amount
        self.print_log("Min surge amount: {}".format(self.min_surge_amount))

        self.min_surge_volume = min_surge_volume
        self.print_log("Min surge volume: {}".format(self.min_surge_volume))

        # at least 4% change for surge
        self.min_surge_change_ratio = min_surge_change_ratio
        self.print_log("Min gap change: {}%".format(
            round(self.min_surge_change_ratio * 100, 2)))

        self.avg_confirm_volume = avg_confirm_volume
        self.print_log("Avg confirm volume: {}".format(
            self.avg_confirm_volume))

        self.order_amount_limit = order_amount_limit
        self.print_log("Buy order limit: {}".format(self.order_amount_limit))

        # observe timeout in seconds
        self.observe_timeout_in_sec = observe_timeout_in_sec
        self.print_log("Observe timeout: {} sec".format(
            self.observe_timeout_in_sec))

        # buy after sell interval in seconds
        self.trade_interval_in_sec = trade_interval_in_sec
        self.print_log("Trade interval: {} sec".format(
            self.trade_interval_in_sec))

        # pending order timeout in seconds
        self.pending_order_timeout_in_sec = pending_order_timeout_in_sec
        self.print_log("Pending order timeout: {} sec".format(
            self.pending_order_timeout_in_sec))

        # holding order timeout in seconds
        self.holding_order_timeout_in_sec = holding_order_timeout_in_sec
        self.print_log("Holding order timeout: {} sec".format(
            self.holding_order_timeout_in_sec))

        self.max_bid_ask_gap_ratio = max_bid_ask_gap_ratio
        self.print_log("Max bid ask gap: {}%".format(
            round(self.max_bid_ask_gap_ratio * 100, 2)))

        self.target_profit_ratio = target_profit_ratio
        self.print_log("Target profit rate: {}%".format(
            round(self.target_profit_ratio * 100, 2)))

        self.stop_loss_ratio = stop_loss_ratio
        self.print_log("Stop loss rate: {}%".format(
            round(self.stop_loss_ratio * 100, 2)))

        self.blacklist_timeout_in_sec = blacklist_timeout_in_sec
        self.print_log("Blacklist timeout: {} sec".format(
            self.blacklist_timeout_in_sec))

        self.swing_position_amount_limit = swing_position_amount_limit
        self.print_log("Swing position amount limit: {}".format(
            self.swing_position_amount_limit))

        self.max_prev_day_close_gap_ratio = max_prev_day_close_gap_ratio
        self.print_log("Max prev day close gap ratio: {}".format(
            self.max_prev_day_close_gap_ratio))

        self.min_relative_volume = min_relative_volume
        self.print_log("Relative volume for entry: {}".format(
            self.min_relative_volume))

        self.min_earning_gap_ratio = min_earning_gap_ratio
        self.print_log("Earning gap ratio for entry: {}".format(
            self.min_earning_gap_ratio))

        self.day_trade_usable_cash_threshold = day_trade_usable_cash_threshold
        self.print_log("Usable cash threshold for day trade: {}".format(
            self.day_trade_usable_cash_threshold))

        return True

    def init_tracking_stats_if_not(self, ticker):
        symbol = ticker['symbol']
        # init trading stats
        if symbol not in self.tracking_stats:
            self.tracking_stats[symbol] = {
                "trades": 0,
                "win_trades": 0,
                "lose_trades": 0,
                "continue_lose_trades": 0,
                "last_trade_high": None,
                "last_trade_time": None,
            }

    def get_init_tracking_ticker(self, symbol, ticker_id, prev_close=None, prev_high=None):
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            "pending_buy": False,
            "pending_sell": False,
            "pending_order_id": None,
            "pending_order_time": None,
            "order_filled_time": None,
            "last_profit_loss_rate": None,
            "last_sell_time": None,
            "positions": 0,
            "start_time": datetime.now(),
            "stop_loss": None,
            # paper trade do not have stop trailing order, this value keep track of max P&L
            "max_profit_loss_rate": 0,
            "exit_note": None,
            "prev_close": prev_close,
            "prev_high": prev_high,
            "resubmit_count": 0,
        }

    def get_init_error_short_ticker(self, symbol, ticker_id):
        return {
            "symbol": symbol,
            "ticker_id": ticker_id,
            # pending buy back order id
            "pending_order_id": None,
            # pending buy back order time
            "pending_order_time": None,
        }

    def check_entry(self):
        return False

    def check_stop_loss(self):
        return False

    def check_exit(self):
        return False

    def check_trading_hour(self):
        return True

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
            if order_filled:
                # remove
                del self.error_short_tickers[symbol]
                self.print_log(
                    "Short cover order <{}>[{}] filled".format(symbol, ticker_id))
            else:
                # check order timeout
                if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                    # cancel timeout order
                    if webullsdk.cancel_order(ticker['pending_order_id']):
                        # remove, let function re-submit again
                        del self.error_short_tickers[symbol]
                    else:
                        self.print_log(
                            "Failed to cancel timeout short cover order <{}>[{}]!".format(symbol, ticker_id))
        for position in positions:
            # if short position
            position_size = int(position['position'])
            if position_size < 0:
                symbol = position['ticker']['symbol']
                ticker_id = position['ticker']['tickerId']
                if symbol not in self.error_short_tickers:
                    self.error_short_tickers[symbol] = self.get_init_tracking_ticker(
                        symbol, ticker_id)
                    last_price = float(position['lastPrice'])
                    # in order to buy, increase 1% to buy
                    buy_price = round(last_price*1.01, 2)
                    # submit buy back order
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=buy_price,
                        quant=abs(position_size))
                    self.print_log("🟢 Submit short cover order <{}>[{}], quant: {}, limit price: {}".format(
                        symbol, ticker_id, abs(position_size), buy_price))
                    if 'msg' in order_response:
                        self.print_log(order_response['msg'])
                    elif 'orderId' in order_response:
                        self.error_short_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        self.error_short_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                    else:
                        self.print_log(
                            "⚠️  Invalid short cover order response: {}".format(order_response))

    def check_buy_order_filled(self, ticker, resubmit=False, stop_tracking=False):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        self.print_log(
            "Checking buy order <{}>[{}] filled...".format(symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return False
        order_filled = False
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = True
                # order filled
                quantity = int(position['position'])
                cost = float(position['costPrice'])
                utils.save_webull_order_note(
                    ticker['pending_order_id'], setup=self.get_setup(), note="Entry point.")
                # update tracking_tickers
                self.tracking_tickers[symbol]['positions'] = quantity
                self.tracking_tickers[symbol]['pending_buy'] = False
                self.tracking_tickers[symbol]['pending_order_id'] = None
                self.tracking_tickers[symbol]['pending_order_time'] = None
                self.tracking_tickers[symbol]['resubmit_count'] = 0
                self.tracking_tickers[symbol]['order_filled_time'] = datetime.now(
                )
                self.print_log("Buy order <{}>[{}] filled, cost: {}".format(
                    symbol, ticker_id, cost))
                # remove from monitor
                if stop_tracking:
                    del self.tracking_tickers[symbol]
                break
        if not order_filled:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(ticker['pending_order_id'], setup=self.get_setup(
                    ), note="Buy order timeout, canceled!")
                    self.print_log(
                        "Buy order <{}>[{}] timeout, canceled!".format(symbol, ticker_id))
                    # resubmit buy order
                    if resubmit and self.tracking_tickers[symbol]['resubmit_count'] <= 10:
                        quote = webullsdk.get_quote(ticker_id=ticker_id)
                        if quote == None:
                            return
                        ask_price = float(
                            quote['depth']['ntvAggAskList'][0]['price'])
                        buy_position_amount = self.get_buy_order_limit(symbol)
                        buy_quant = (int)(buy_position_amount / ask_price)
                        order_response = webullsdk.buy_limit_order(
                            ticker_id=ticker_id,
                            price=ask_price,
                            quant=buy_quant)
                        self.print_log("Resubmit buy order <{}>[{}], quant: {}, limit price: {}".format(
                            symbol, ticker_id, buy_quant, ask_price))
                        self.update_pending_buy_order(symbol, order_response)
                        if 'orderId' in order_response:
                            utils.save_webull_order_note(
                                order_response['orderId'], setup=self.get_setup(), note="Resubmit buy order.")
                        self.tracking_tickers[symbol]['resubmit_count'] += 1
                    else:
                        self.tracking_tickers[symbol]['pending_buy'] = False
                        self.tracking_tickers[symbol]['pending_order_id'] = None
                        self.tracking_tickers[symbol]['pending_order_time'] = None
                        self.tracking_tickers[symbol]['resubmit_count'] = 0
                else:
                    self.print_log(
                        "Failed to cancel timeout buy order <{}>[{}]!".format(symbol, ticker_id))

        # check short order
        self.check_error_short_order(positions)

        return order_filled

    def check_sell_order_filled(self, ticker, resubmit=True, stop_tracking=True):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        self.print_log(
            "Checking sell order <{}>[{}] filled...".format(symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return False
        order_filled = True
        for position in positions:
            # make sure position is positive
            if position['ticker']['symbol'] == symbol and float(position['position']) > 0:
                order_filled = False
        if order_filled:
            # check if have any exit note
            exit_note = self.tracking_tickers[symbol]['exit_note']
            if exit_note:
                utils.save_webull_order_note(
                    self.tracking_tickers[symbol]['pending_order_id'], setup=self.get_setup(), note=exit_note)
            # update tracking_tickers
            self.tracking_tickers[symbol]['positions'] = 0
            self.tracking_tickers[symbol]['pending_sell'] = False
            self.tracking_tickers[symbol]['pending_order_id'] = None
            self.tracking_tickers[symbol]['pending_order_time'] = None
            self.tracking_tickers[symbol]['last_sell_time'] = datetime.now()
            self.tracking_tickers[symbol]['exit_note'] = None
            self.tracking_tickers[symbol]['resubmit_count'] = 0
            # last_profit_loss_rate = self.tracking_tickers[symbol]['last_profit_loss_rate']
            # # keep in track if > 10% profit, prevent buy back too quick
            # if last_profit_loss_rate != None and last_profit_loss_rate < 0.1:
            # remove from monitor
            if stop_tracking:
                del self.tracking_tickers[symbol]
            self.print_log(
                "Sell order <{}>[{}] filled".format(symbol, ticker_id))
            # update account status
            account_data = webullsdk.get_account()
            utils.save_webull_account(account_data)
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(ticker['pending_order_id'], setup=self.get_setup(
                    ), note="Sell order timeout, canceled!")
                    self.print_log(
                        "Sell order <{}>[{}] timeout, canceled!".format(symbol, ticker_id))
                    # resubmit sell order
                    if resubmit and self.tracking_tickers[symbol]['resubmit_count'] <= 10:
                        quote = webullsdk.get_quote(ticker_id=ticker_id)
                        if quote == None:
                            return
                        bid_price = float(
                            quote['depth']['ntvAggBidList'][0]['price'])
                        holding_quantity = ticker['positions']
                        order_response = webullsdk.sell_limit_order(
                            ticker_id=ticker_id,
                            price=bid_price,
                            quant=holding_quantity)
                        self.print_log("Resubmit sell order <{}>[{}], quant: {}, limit price: {}".format(
                            symbol, ticker_id, holding_quantity, bid_price))
                        self.update_pending_sell_order(symbol, order_response)
                        if 'orderId' in order_response:
                            utils.save_webull_order_note(
                                order_response['orderId'], setup=self.get_setup(), note="Resubmit sell order.")
                        self.tracking_tickers[symbol]['resubmit_count'] += 1
                    else:
                        self.tracking_tickers[symbol]['pending_sell'] = False
                        self.tracking_tickers[symbol]['pending_order_id'] = None
                        self.tracking_tickers[symbol]['pending_order_time'] = None
                        self.tracking_tickers[symbol]['resubmit_count'] = 0
                else:
                    self.print_log(
                        "Failed to cancel timeout sell order <{}>[{}]!".format(symbol, ticker_id))

        # check short order
        self.check_error_short_order(positions)

        return order_filled

    def update_trading_stats(self, symbol, price, cost, profit_loss_rate):
        # after perform 1 trade
        self.tracking_stats[symbol]['trades'] += 1
        self.tracking_stats[symbol]['last_trade_time'] = datetime.now()
        last_trade_high = self.tracking_stats[symbol]['last_trade_high'] or 0
        self.tracking_stats[symbol]['last_trade_high'] = max(
            cost, price, last_trade_high)
        if profit_loss_rate > 0:
            self.tracking_stats[symbol]['win_trades'] += 1
            self.tracking_stats[symbol]['continue_lose_trades'] = 0
        else:
            self.tracking_stats[symbol]['lose_trades'] += 1
            self.tracking_stats[symbol]['continue_lose_trades'] += 1

    def update_pending_buy_order(self, symbol, order_response, stop_loss=None):
        if 'msg' in order_response:
            self.print_log(order_response['msg'])
        elif 'orderId' in order_response:
            # mark pending buy
            self.tracking_tickers[symbol]['pending_buy'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            # set stop loss at prev low
            self.tracking_tickers[symbol]['stop_loss'] = stop_loss
        else:
            self.print_log(
                "⚠️  Invalid buy order response: {}".format(order_response))

    def update_pending_sell_order(self, symbol, order_response, exit_note=""):
        if 'msg' in order_response:
            self.print_log(order_response['msg'])
        elif 'orderId' in order_response:
            # mark pending sell
            self.tracking_tickers[symbol]['pending_sell'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            self.tracking_tickers[symbol]['exit_note'] = exit_note
        else:
            self.print_log(
                "⚠️  Invalid sell order response: {}".format(order_response))

    def add_swing_position(self, symbol, order_response, cost, quant, buy_time, setup):
        if 'msg' in order_response:
            self.print_log(order_response['msg'])
        elif 'orderId' in order_response:
            # create swing position
            position = SwingPosition(
                symbol=symbol,
                order_id=order_response['orderId'],
                cost=cost,
                quantity=quant,
                buy_time=buy_time,
                buy_date=buy_time.date(),
                setup=setup,
            )
            position.save()
        else:
            self.print_log(
                "⚠️  Invalid swing buy order response: {}".format(order_response))

    def add_swing_trade(self, symbol, order_response, position, price, sell_time):
        if 'msg' in order_response:
            self.print_log(order_response['msg'])
        elif 'orderId' in order_response:
            # create swing position
            trade = SwingTrade(
                symbol=symbol,
                buy_order_id=position.order_id,
                buy_price=position.cost,
                quantity=position.quantity,
                buy_time=position.buy_time,
                buy_date=position.buy_date,
                setup=position.setup,
                sell_order_id=order_response['orderId'],
                sell_price=price,
                sell_time=sell_time,
                sell_date=sell_time.date(),
            )
            trade.save()
        else:
            self.print_log(
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

    def clear_position(self, ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        if holding_quantity == 0:
            # remove from monitor
            del self.tracking_tickers[symbol]
            return

        quote = webullsdk.get_quote(ticker_id=ticker_id)
        if quote == None:
            return
        bid_price = float(quote['depth']['ntvAggBidList'][0]['price'])
        order_response = webullsdk.sell_limit_order(
            ticker_id=ticker_id,
            price=bid_price,
            quant=holding_quantity)
        self.print_log("🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
            symbol, ticker_id, holding_quantity, bid_price))
        self.update_pending_sell_order(
            symbol, order_response, exit_note="Clear position.")

    def get_setup(self):
        return 999

    def get_buy_order_limit(self, symbol):
        return self.order_amount_limit
