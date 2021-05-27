# -*- coding: utf-8 -*-

# Base trading class

from datetime import datetime, timedelta
from webull_trader.models import TradingSettings
from sdk import webullsdk
from scripts import utils


class TradingBase:

    def __init__(self, paper=True):
        self.paper = paper
        # init trading variables
        self.tracking_tickers = {}
        self.trading_stats = {}

    # load settings
    def load_settings(self):

        trading_settings = TradingSettings.objects.first()
        if not trading_settings:
            return False

        self.min_surge_amount = trading_settings.min_surge_amount
        print("[{}] Min surge amount: {}".format(
            utils.get_now(), self.min_surge_amount))
        self.min_surge_volume = trading_settings.min_surge_volume
        print("[{}] Min surge volume: {}".format(
            utils.get_now(), self.min_surge_volume))
        # at least 4% change for surge
        self.min_surge_change_ratio = trading_settings.min_surge_change_ratio
        print("[{}] Min gap change: {}%".format(
            utils.get_now(), round(self.min_surge_change_ratio * 100, 2)))
        self.avg_confirm_volume = trading_settings.avg_confirm_volume
        print("[{}] Avg confirm volume: {}".format(
            utils.get_now(), self.avg_confirm_volume))
        self.order_amount_limit = trading_settings.order_amount_limit
        print("[{}] Buy order limit: {}".format(
            utils.get_now(), self.order_amount_limit))
        # observe timeout in seconds
        self.observe_timeout_in_sec = trading_settings.observe_timeout_in_sec
        print("[{}] Observe timeout: {} sec".format(
            utils.get_now(), self.observe_timeout_in_sec))
        # buy after sell interval in seconds
        self.trade_interval_in_sec = trading_settings.trade_interval_in_sec
        print("[{}] Trade interval: {} sec".format(
            utils.get_now(), self.trade_interval_in_sec))
        # pending order timeout in seconds
        self.pending_order_timeout_in_sec = trading_settings.pending_order_timeout_in_sec
        print("[{}] Pending order timeout: {} sec".format(
            utils.get_now(), self.pending_order_timeout_in_sec))
        # holding order timeout in seconds
        self.holding_order_timeout_in_sec = trading_settings.holding_order_timeout_in_sec
        print("[{}] Holding order timeout: {} sec".format(
            utils.get_now(), self.holding_order_timeout_in_sec))
        # refresh login interval minutes
        self.refresh_login_interval_in_min = trading_settings.refresh_login_interval_in_min
        print("[{}] Refresh login timeout: {} min".format(
            utils.get_now(), self.refresh_login_interval_in_min))
        self.max_bid_ask_gap_ratio = trading_settings.max_bid_ask_gap_ratio
        print("[{}] Max bid ask gap: {}%".format(
            utils.get_now(), round(self.max_bid_ask_gap_ratio * 100, 2)))
        self.target_profit_ratio = trading_settings.target_profit_ratio
        print("[{}] Target profit rate: {}%".format(
            utils.get_now(), round(self.target_profit_ratio * 100, 2)))
        self.stop_loss_ratio = trading_settings.stop_loss_ratio
        print("[{}] Stop loss rate: {}%".format(
            utils.get_now(), round(self.stop_loss_ratio * 100, 2)))
        self.blacklist_timeout_in_sec = trading_settings.blacklist_timeout_in_sec
        print("[{}] Blacklist timeout: {} sec".format(
            utils.get_now(), self.blacklist_timeout_in_sec))

        return True

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
        }

    def check_buy_order_filled(self, ticker):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] Checking buy order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
        order_filled = False
        for position in positions:
            if position['ticker']['symbol'] == symbol:
                order_filled = True
                quantity = int(position['position'])
                cost = float(position['costPrice'])
                utils.save_webull_order_note(
                    ticker['pending_order_id'], setup=self.get_setup(), note="Entry point.")
                # update tracking_tickers
                self.tracking_tickers[symbol]['positions'] = quantity
                self.tracking_tickers[symbol]['pending_buy'] = False
                self.tracking_tickers[symbol]['pending_order_id'] = None
                self.tracking_tickers[symbol]['pending_order_time'] = None
                self.tracking_tickers[symbol]['order_filled_time'] = datetime.now(
                )
                print("[{}] Buy order <{}>[{}] filled, cost: {}".format(
                    utils.get_now(), symbol, ticker_id, cost))
                break
        if not order_filled:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(
                        ticker['pending_order_id'], note="Buy order timeout, canceled!")
                    print("[{}] Buy order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                    self.tracking_tickers[symbol]['pending_buy'] = False
                    self.tracking_tickers[symbol]['pending_order_id'] = None
                    self.tracking_tickers[symbol]['pending_order_time'] = None
                else:
                    print("[{}] Failed to cancel timeout buy order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def check_sell_order_filled(self, ticker, stop_tracking=True):
        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        print("[{}] Checking sell order <{}>[{}] filled...".format(
            utils.get_now(), symbol, ticker_id))
        positions = webullsdk.get_positions()
        if positions == None:
            return
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
                    self.tracking_tickers[symbol]['pending_order_id'], note=exit_note)
            # update tracking_tickers
            self.tracking_tickers[symbol]['positions'] = 0
            self.tracking_tickers[symbol]['pending_sell'] = False
            self.tracking_tickers[symbol]['pending_order_id'] = None
            self.tracking_tickers[symbol]['pending_order_time'] = None
            self.tracking_tickers[symbol]['last_sell_time'] = datetime.now()
            self.tracking_tickers[symbol]['exit_note'] = None
            # last_profit_loss_rate = self.tracking_tickers[symbol]['last_profit_loss_rate']
            # # keep in track if > 10% profit, prevent buy back too quick
            # if last_profit_loss_rate != None and last_profit_loss_rate < 0.1:
            # remove from monitor
            if stop_tracking:
                del self.tracking_tickers[symbol]
            print("[{}] Sell order <{}>[{}] filled".format(
                utils.get_now(), symbol, ticker_id))
            # update account status
            account_data = webullsdk.get_account()
            utils.save_webull_account(account_data)
        else:
            # check order timeout
            if (datetime.now() - ticker['pending_order_time']) >= timedelta(seconds=self.pending_order_timeout_in_sec):
                # cancel timeout order
                if webullsdk.cancel_order(ticker['pending_order_id']):
                    utils.save_webull_order_note(
                        ticker['pending_order_id'], note="Sell order timeout, canceled!")
                    print("[{}] Sell order <{}>[{}] timeout, canceled!".format(
                        utils.get_now(), symbol, ticker_id))
                    # resubmit sell order
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
                    print("[{}] Resubmit sell order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        utils.save_webull_order_note(
                            order_response['orderId'], note="Resubmit sell order.")
                        # mark pending sell
                        self.tracking_tickers[symbol]['pending_sell'] = True
                        self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                else:
                    print("[{}] Failed to cancel timeout sell order <{}>[{}]!".format(
                        utils.get_now(), symbol, ticker_id))

    def update_pending_buy_order(self, symbol, order_response, stop_loss=None):
        if 'msg' in order_response:
            print("[{}] {}".format(
                utils.get_now(), order_response['msg']))
        elif 'orderId' in order_response:
            # mark pending buy
            self.tracking_tickers[symbol]['pending_buy'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            # set stop loss at prev low
            self.tracking_tickers[symbol]['stop_loss'] = stop_loss

    def update_pending_sell_order(self, symbol, order_response, exit_note=""):
        if 'msg' in order_response:
            print("[{}] {}".format(utils.get_now(), order_response['msg']))
        elif 'orderId' in order_response:
            # mark pending sell
            self.tracking_tickers[symbol]['pending_sell'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )
            self.tracking_tickers[symbol]['exit_note'] = exit_note

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
        print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
            utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
        if 'msg' in order_response:
            print("[{}] {}".format(utils.get_now(), order_response['msg']))
        else:
            # mark pending sell
            self.tracking_tickers[symbol]['pending_sell'] = True
            self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
            self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
            )

    def get_setup(self):
        return 999

    def get_buy_order_limit(self, symbol):
        return self.order_amount_limit

    def check_if_track_symbol(self, symbol):
        # # check if sell not long ago
        # if symbol in self.trading_stats and (datetime.now() - self.trading_stats[symbol]['last_trade_time']) <= timedelta(seconds=100):
        #     return False
        return True

    def check_if_has_enough_volume(self, bars):
        enough_volume = True
        # only check for regular hour now
        if utils.is_regular_market_hour():
            total_volume = 0
            total_count = 0
            for index, row in bars.iterrows():
                time = index.to_pydatetime()
                if (time.hour == 9 and time.minute > 30) or time.hour > 9:
                    volume = row["volume"]
                    total_volume += volume
                    total_count += 1
            if total_count > 0:
                avg_volume = total_volume / total_count
                confirm_avg_volume = utils.get_avg_confirm_volume()
                if avg_volume < confirm_avg_volume:
                    enough_volume = False
        return enough_volume
