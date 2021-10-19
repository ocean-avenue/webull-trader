from datetime import datetime, timedelta
from common import utils, db, config
from sdk import webullsdk
from webull_trader.models import DayPosition, WebullOrder


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
        if len(self.current_orders) > 0:
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


# Tracking ticker class
class TrackingTicker:

    def __init__(self, symbol: str, ticker_id: str, prev_close: float = None, prev_high: float = None):
        self.symbol: str = symbol
        self.ticker_id: str = ticker_id
        self.pending_order_id: str = None
        self.pending_order_time: datetime = None
        self.last_buy_time: datetime = None
        self.last_sell_time: datetime = None
        self.last_profit_loss_rate: float = None
        self.positions: int = 0
        self.start_time: datetime = datetime.now()
        self.target_profit: float = None
        self.stop_loss: float = None
        # paper trade do not have stop trailing order, this value keep track of max P&L
        self.max_profit_loss_rate: float = 0
        self.exit_note: str = None
        self.prev_close: float = prev_close
        self.prev_high: float = prev_high
        self.resubmit_order_count: int = 0
        self.initial_cost: float = None
        self.exit_period: int = None
        self.position_obj: DayPosition = None

    def get_id(self) -> str:
        return self.ticker_id

    def get_symbol(self) -> str:
        return self.symbol

    def has_pending_order(self) -> bool:
        return self.pending_order_id != None

    def get_positions(self) -> int:
        return self.positions

    def get_last_buy_time(self) -> datetime:
        return self.last_buy_time

    def set_initial_cost(self, initial_cost: float):
        self.initial_cost = initial_cost

    def get_initial_cost(self) -> float:
        return self.initial_cost

    def set_exit_period(self, exit_period: int):
        self.exit_period = exit_period

    def get_exit_period(self) -> int:
        return self.exit_period

    def set_position_obj(self, position_obj: DayPosition):
        self.position_obj = position_obj

    def get_position_obj(self) -> DayPosition:
        return self.position_obj

    def is_timeout(self) -> bool:
        if self.last_buy_time and (datetime.now() - self.last_buy_time) >= timedelta(seconds=config.OBSERVE_TIMEOUT_IN_SEC):
            return True
        elif (datetime.now() - self.start_time) >= timedelta(seconds=config.OBSERVE_TIMEOUT_IN_SEC):
            return True
        return False

    def is_just_sold(self) -> bool:
        if self.last_sell_time and (datetime.now() - self.last_sell_time) <= timedelta(seconds=config.TRADE_INTERVAL_IN_SEC):
            return True
        return False


# Trading tracker class
class TradingTracker:

    def __init__(self, paper: bool = True):
        self.paper: bool = paper
        self.tickers: dict = {}
        self.status: dict = {}

    def start_tracking(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        if symbol not in self.tickers:
            # add tracking ticker
            self.tickers[symbol] = ticker
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

    def get_tracking_tickers(self):
        return list(self.tracking_tickers)

    def get_tracking_ticker(self, symbol):
        return self.tracking_tickers[symbol]

    def stop_tracking(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        if symbol in self.tickers:
            del self.tickers[symbol]

    def update_tracking(self, symbol, ticker_update):
        if symbol in self.tickers:
            self.tickers[symbol].update(ticker_update)
