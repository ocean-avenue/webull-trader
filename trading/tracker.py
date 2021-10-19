from datetime import datetime
from common import utils, db
from sdk import webullsdk
from webull_trader.models import WebullOrder


# Order tracker class
class OrderTracker:

    def __init__(self, paper=True):
        self.paper = paper
        self.current_orders = {}

    def _order_done(self, status):
        if status == webullsdk.ORDER_STATUS_CANCELED or status == webullsdk.ORDER_STATUS_FILLED or \
                status == webullsdk.ORDER_STATUS_PARTIALLY_FILLED or status == webullsdk.ORDER_STATUS_FAILED:
            return True
        return False

    def start_tracking(self, order_response, setup):
        order_id = utils.get_order_id_from_response(
            order_response, paper=self.paper)
        if order_id:
            self.current_orders[order_id] = {
                # 'status': webullsdk.ORDER_STATUS_PENDING,
                'setup': setup,
            }

    def update_orders(self):
        orders = webullsdk.get_history_orders(count=20)

        for order_data in orders:
            # save order to db
            db.save_webull_order(order_data, self.paper)

        for order_id in list(self.current_orders):
            order = WebullOrder.objects.filter(order_id=order_id).first()
            if order:
                # order done
                if self._order_done(order.status):
                    open_order = self.current_orders[order_id]
                    # update setup
                    order.setup = open_order['setup']
                    order.save()
                    del self.current_orders[order_id]


# Ticker tracker class
class TickerTracker:

    def __init__(self, paper=True):
        self.paper = paper
        self.tickers = {}
        self.status = {}

    def start_tracking(self, symbol, ticker_id, prev_close=None, prev_high=None):
        if symbol not in self.tickers:
            # init tracking ticker
            self.tickers[symbol] = {
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
        # init tracking stats if not
        if symbol not in self.status:
            self.status[symbol] = {
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

    def is_tracking(self, symbol):
        if symbol in self.tickers:
            return True
        return False

    def stop_tracking(self, symbol):
        if symbol in self.tickers:
            del self.tickers[symbol]

    def update_tracking(self, symbol, ticker_update):
        if symbol in self.tickers:
            self.tickers[symbol].update(ticker_update)