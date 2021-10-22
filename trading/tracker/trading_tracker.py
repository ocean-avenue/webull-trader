from typing import List, Optional
from datetime import datetime, timedelta
from common import config
from webull_trader.models import DayPosition


# Tracking ticker class, data only available during ticker session
class TrackingTicker:

    def __init__(self, symbol: str, ticker_id: str):
        self.symbol: str = symbol
        self.ticker_id: str = ticker_id
        self.pending_buy: bool = False
        self.pending_sell: bool = False
        self.pending_cancel: bool = False
        self.pending_order_id: Optional[str] = None
        self.pending_order_time: Optional[datetime] = None
        self.last_buy_time: Optional[datetime] = None
        self.last_sell_time: Optional[datetime] = None
        self.last_profit_loss_rate: float = 0.0
        # paper trade do not have stop trailing order, this value keep track of max P&L
        self.max_profit_loss_rate: float = 0.0
        self.positions: int = 0
        self.start_time: datetime = datetime.now()
        self.target_profit: Optional[float] = None
        self.stop_loss: Optional[float] = None
        self.prev_close: Optional[float] = None
        self.prev_high: Optional[float] = None
        self.resubmit_order_count: int = 0
        self.initial_cost: Optional[float] = None
        self.exit_period: Optional[int] = None
        self.position_obj: Optional[DayPosition] = None

    def get_id(self) -> str:
        return self.ticker_id

    def get_symbol(self) -> str:
        return self.symbol

    def set_pending_buy(self, pending_buy: bool):
        self.pending_buy = pending_buy

    def is_pending_buy(self) -> bool:
        return self.pending_buy

    def set_pending_sell(self, pending_sell: bool):
        self.pending_sell = pending_sell

    def get_pending_sell(self) -> bool:
        return self.pending_sell

    def set_pending_cancel(self, pending_cancel: bool):
        self.pending_cancel = pending_cancel

    def get_pending_cancel(self) -> bool:
        return self.pending_cancel

    def set_pending_order_id(self, order_id: str):
        self.pending_order_id = order_id

    def get_pending_order_id(self) -> Optional[str]:
        return self.pending_order_id

    def set_pending_order_time(self, order_time: datetime):
        self.pending_order_time = order_time

    def get_pending_order_time(self) -> Optional[datetime]:
        return self.pending_order_time

    def get_start_time(self) -> datetime:
        return self.start_time

    def set_target_profit(self, target_profit: float):
        self.target_profit = target_profit

    def get_target_profit(self) -> Optional[float]:
        return self.target_profit

    def set_stop_loss(self, stop_loss: float):
        self.stop_loss = stop_loss

    def get_stop_loss(self) -> Optional[float]:
        return self.stop_loss

    def set_last_profit_loss_rate(self, profit_loss_rate: float):
        self.last_profit_loss_rate = profit_loss_rate

    def get_last_profit_loss_rate(self) -> float:
        return self.last_profit_loss_rate

    def set_max_profit_loss_rate(self, profit_loss_rate: float):
        self.max_profit_loss_rate = profit_loss_rate

    def get_max_profit_loss_rate(self) -> float:
        return self.max_profit_loss_rate

    def set_prev_close(self, prev_close: float):
        self.prev_close = prev_close

    def get_prev_close(self) -> Optional[float]:
        return self.prev_close

    def set_prev_high(self, prev_high: float):
        self.prev_high = prev_high

    def get_prev_high(self) -> Optional[float]:
        return self.prev_high

    def set_positions(self, positions: int):
        self.positions = positions

    def get_positions(self) -> int:
        return self.positions

    def set_last_buy_time(self, buy_time: datetime):
        self.last_buy_time = buy_time

    def get_last_buy_time(self) -> Optional[datetime]:
        return self.last_buy_time

    def set_last_sell_time(self, sell_time: datetime):
        self.last_sell_time = sell_time

    def get_last_sell_time(self) -> Optional[datetime]:
        return self.last_sell_time

    def set_initial_cost(self, initial_cost: float):
        self.initial_cost = initial_cost

    def get_initial_cost(self) -> Optional[float]:
        return self.initial_cost

    def set_exit_period(self, exit_period: int):
        self.exit_period = exit_period

    def get_exit_period(self) -> Optional[int]:
        return self.exit_period

    def inc_resubmit_order_count(self):
        self.resubmit_order_count += 1

    def get_resubmit_order_count(self) -> int:
        return self.resubmit_order_count

    def set_position_obj(self, position_obj: DayPosition):
        self.position_obj = position_obj

    def get_position_obj(self) -> Optional[DayPosition]:
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


# Tracking status class, data will persistent during whole trading session
class TrackingStatus:

    def __init__(self, symbol: str):
        self.symbol: str = symbol
        self.trades: int = 0
        self.win_trades: int = 0
        self.lose_trades: int = 0
        self.continue_lose_trades: int = 0
        self.last_high_price: Optional[float] = None
        self.sector: Optional[str] = None
        self.free_float: Optional[float] = None
        self.turnover_rate: Optional[float] = None
        self.last_trade_time: Optional[datetime] = None

    def inc_trades(self):
        self.trades += 1

    def get_trades(self) -> int:
        return self.trades

    def inc_win_trades(self):
        self.win_trades += 1

    def get_win_trades(self) -> int:
        return self.win_trades

    def inc_lose_trades(self):
        self.lose_trades += 1

    def get_lose_trades(self) -> int:
        return self.lose_trades

    def inc_continue_lose_trades(self):
        self.continue_lose_trades += 1

    def get_continue_lose_trades(self) -> int:
        return self.continue_lose_trades

    def set_last_high_price(self, high_price: float):
        self.last_high_price = high_price

    def get_last_high_price(self) -> Optional[float]:
        return self.last_high_price

    def set_sector(self, sector: str):
        self.sector = sector

    def get_sector(self) -> Optional[str]:
        return self.sector

    def set_free_float(self, free_float: float):
        self.free_float = free_float

    def get_free_float(self) -> Optional[float]:
        return self.free_float

    def set_turnover_rate(self, turnover_rate: float):
        self.turnover_rate = turnover_rate

    def get_turnover_rate(self) -> Optional[float]:
        return self.turnover_rate

    def set_last_trade_time(self, trade_time: datetime):
        self.last_trade_time = trade_time

    def get_last_trade_time(self) -> Optional[datetime]:
        return self.last_trade_time


# Trading tracker class
class TradingTracker:

    def __init__(self, paper: bool = True):
        self.paper: bool = paper
        self.tickers: dict = {}
        self.status: dict = {}

    def start_tracking(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        if symbol not in self.tickers:
            # add tracking ticker
            self.tickers[symbol] = ticker
        # init tracking stats if not
        if symbol not in self.status:
            # add tracking status
            tracking_status = TrackingStatus(symbol, ticker_id)
            self.status[symbol] = tracking_status

    def stop_tracking(self, ticker: TrackingTicker):
        symbol = ticker.get_symbol()
        if symbol in self.tickers:
            del self.tickers[symbol]

    def is_tracking(self, symbol: str) -> bool:
        if symbol in self.tickers:
            return True
        return False

    def get_tickers(self) -> List[TrackingTicker]:
        return list(self.tickers)

    def get_ticker(self, symbol) -> Optional[TrackingTicker]:
        if self.is_tracking(symbol):
            return self.tickers[symbol]
        return None

    def get_status(self, symbol) -> TrackingStatus:
        if symbol not in self.status:
            self.status[symbol] = TrackingStatus(symbol)
        return self.status[symbol]
