# -*- coding: utf-8 -*-

# Base backtest class

from datetime import datetime, date
from logger import trading_logger
from common import db
from common.enums import ActionType, OrderType, SetupType, TimeInForceType, TradingHourType
from trading.tracker.trading_tracker import TradingTracker
from backtest.tracker.account_tracker import BacktestAccountTracker
from backtest.tracker.order_tracker import BacktestOrderTracker
from webull_trader.models import WebullOrder


class BacktestStrategyBase:

    import pandas as pd
    from common.enums import SetupType, TradingHourType
    from trading.tracker.trading_tracker import TrackingTicker

    INIT_BALANCE = 30000.0

    def __init__(self, trading_date: date, trading_hour: TradingHourType = TradingHourType.REGULAR):
        # init strategy variables
        self.trading_date: date = trading_date
        self.trading_hour: TradingHourType = trading_hour
        self.trading_end: bool = False
        self.trading_tracker: TradingTracker = TradingTracker()
        self.account_tracker = BacktestAccountTracker(
            balance=self.INIT_BALANCE)
        self.order_tracker = BacktestOrderTracker()

        self.trading_time: datetime = datetime.now()

    def set_trading_time(self, time: datetime):
        self.trading_time = time

    def begin(self):
        pass

    def update(self):
        pass

    def end(self):
        pass

    def final(self):
        pass

    def get_tag(self) -> str:
        return "BacktestStrategyBase"

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

    def is_regular_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.REGULAR

    def is_pre_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.BEFORE_MARKET_OPEN

    def is_after_market_hour(self) -> bool:
        return self.trading_hour == TradingHourType.AFTER_MARKET_CLOSE

    def is_extended_market_hour(self) -> bool:
        return self.is_pre_market_hour() or self.is_after_market_hour()

    def check_can_trade_ticker(self, ticker: TrackingTicker):
        return True

    # submit buy limit order, only use for backtesting
    def submit_buy_limit_order(self, ticker: TrackingTicker, note: str = "Entry point."):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        usable_cash = self.account_tracker.get_cash_balance()
        db.save_webull_min_usable_cash(usable_cash, day=self.trading_date)
        buy_position_amount = self.get_buy_order_limit(ticker)
        if usable_cash <= buy_position_amount:
            trading_logger.log(
                "Not enough cash to buy <{}>, cash left: {}!".format(symbol, usable_cash))
            return
        buy_price = self.get_buy_price(ticker)

        buy_quant = (int)(buy_position_amount / buy_price)
        if buy_quant > 0:
            # create webull buy order
            order_id = self.order_tracker.get_next_order_id()
            trading_logger.log(
                f"🟢 Submit buy order {order_id}, ticker: <{symbol}>, quant: {buy_quant}, limit price: {buy_price}")
            order = db.save_webull_order_backtest({
                'orderId': order_id,
                'ticker': {
                    'symbol': symbol,
                    'tickerId': ticker_id,
                },
                'action': ActionType.BUY,
                'statusStr': 'Filled',
                'orderType': OrderType.LMT,
                'totalQuantity': buy_quant,
                'filledQuantity': buy_quant,
                'avgFilledPrice': buy_price,
                'lmtPrice': buy_price,
                'filled_time': self.trading_time,
                'placedTime': self.trading_time,
                'timeInForce': TimeInForceType.DAY,
            })
            # create day position
            self._on_buy_order_filled(ticker, order)

        else:
            trading_logger.log(
                "Order amount limit not enough for <{}>, price: {}".format(symbol, buy_price))

    def _on_buy_order_filled(self, ticker: TrackingTicker, order: WebullOrder):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
        position_obj = ticker.get_position_obj()
        if position_obj:
            # update position obj
            position_obj.order_ids = f"{position_obj.order_ids},{order_id}"
            position_obj.quantity += order.filled_quantity
            position_obj.total_cost += round(
                order.filled_quantity * order.avg_price, 2)
            position_obj.units += 1
            position_obj.require_adjustment = False
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
        # update account tracker
        self.account_tracker.update_cash_balance(
            -round(order.filled_quantity * order.avg_price, 2))

    # submit sell limit order, only use for backtesting
    def submit_sell_limit_order(self, ticker: TrackingTicker, note: str = "Exit point."):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        holding_quantity = ticker.get_positions()
        sell_price = self.get_sell_price(ticker)
        # create webull buy order
        order_id = self.order_tracker.get_next_order_id()
        trading_logger.log(
            f"🔴 Submit sell order {order_id}, ticker: <{symbol}>, quant: {holding_quantity}, limit price: {sell_price}")
        order = db.save_webull_order_backtest({
            'orderId': order_id,
            'ticker': {
                'symbol': symbol,
                'tickerId': ticker_id,
            },
            'action': ActionType.SELL,
            'statusStr': 'Filled',
            'orderType': OrderType.LMT,
            'totalQuantity': holding_quantity,
            'filledQuantity': holding_quantity,
            'avgFilledPrice': sell_price,
            'lmtPrice': sell_price,
            'filled_time': self.trading_time,
            'placedTime': self.trading_time,
            'timeInForce': TimeInForceType.DAY,
        })
        self._on_sell_order_filled(ticker, order)

    def _on_sell_order_filled(self, ticker: TrackingTicker, order: WebullOrder):
        symbol = ticker.get_symbol()
        ticker_id = ticker.get_id()
        order_id = order.order_id
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
        # update trading stats
        tracking_stat = self.trading_tracker.get_stat(symbol)
        tracking_stat.update_by_trade(trade)
        # update account tracker
        self.account_tracker.update_cash_balance(
            round(order.filled_quantity * order.avg_price, 2))

    # clear all positions
    def clear_positions(self):
        for ticker_id in self.trading_tracker.get_tickers():
            ticker = self.trading_tracker.get_ticker(ticker_id)
            self.clear_position(ticker)

    def clear_position(self, ticker: TrackingTicker):

        holding_quantity = ticker.get_positions()
        if holding_quantity == 0:
            # remove from tracking
            self.trading_tracker.stop_tracking(ticker)
            return

        self.submit_sell_limit_order(ticker, note="Clear position.")

    def get_buy_order_limit(self, ticker: TrackingTicker) -> float:
        if self.is_regular_market_hour():
            return self.order_amount_limit
        return self.extended_order_amount_limit

    def get_buy_price(self, ticker: TrackingTicker) -> float:
        symbol = ticker.get_symbol()
        current_bar = db.get_hist_minute_bar(symbol, self.trading_time)
        return current_bar.close

    def get_sell_price(self, ticker: TrackingTicker) -> float:
        symbol = ticker.get_symbol()
        current_bar = db.get_hist_minute_bar(symbol, self.trading_time)
        return current_bar.close

    def get_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_scale_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0

    def get_dip_stop_loss_price(self, bars: pd.DataFrame) -> float:
        return 0.0
