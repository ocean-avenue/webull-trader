# -*- coding: utf-8 -*-

# Earning day trading class, may holding positions overnight

from django.utils import timezone
from datetime import date, datetime
from webull_trader.models import EarningCalendar, OvernightPosition
from trading.strategy_base import StrategyBase
from webull_trader.enums import SetupType
from sdk import webullsdk
from scripts import utils


class DayTradingEarningsOvernight(StrategyBase):

    def __init__(self, paper, trading_hour):
        super().__init__(paper=paper, trading_hour=trading_hour)
        self.trading_price = {}

    def get_tag(self):
        return "DayTradingEarningsOvernight"

    def get_setup(self):
        return SetupType.DAY_EARNINGS_GAP

    def check_entry(self, ticker, quote):
        if 'pChRatio' in quote and float(quote['pChRatio']) >= self.min_earning_gap_ratio:
            return True
        return False

    def check_stop_loss(self, ticker):
        return (False, None)

    def check_exit(self, ticker):
        if datetime.now().hour > 12:
            return (True, "Sell at 12:00 PM!")
        return (False, None)

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            order_id = ticker['pending_order_id']
            if self.check_buy_order_filled(ticker, resubmit=True, stop_tracking=True):
                # add overnight position
                cost = self.trading_price[symbol]['cost']
                quantity = self.trading_price[symbol]['quantity']
                utils.save_overnight_position(
                    symbol, ticker_id, order_id, self.get_setup(), cost, quantity, timezone.now())
            return

        if ticker['pending_sell']:
            order_id = ticker['pending_order_id']
            if self.check_sell_order_filled(ticker):
                # remove overnight position
                position = OvernightPosition.objects.filter(symbol=symbol).filter(
                    ticker_id=ticker_id).filter(setup=self.get_setup()).first()
                if position:
                    # add overnight trade
                    sell_price = self.trading_price[symbol]['sell_price']
                    utils.save_overnight_trade(
                        symbol, position, order_id, sell_price, timezone.now())
                else:
                    self.print_log(
                        "❌ Cannot find overnight position for <{}>!".format(symbol))
            return

        holding_quantity = ticker['positions']
        # buy in pre/after market hour
        if self.is_extended_market_hour():
            quote = webullsdk.get_quote(ticker_id=ticker_id)
            if quote == None:
                return
            if self.check_entry(ticker, quote):
                ask_price = self.get_ask_price_from_quote(quote)
                if ask_price == None:
                    return
                buy_position_amount = self.get_buy_order_limit(symbol)
                buy_quant = (int)(buy_position_amount / ask_price)
                # submit limit order at ask price
                order_response = webullsdk.buy_limit_order(
                    ticker_id=ticker_id,
                    price=ask_price,
                    quant=buy_quant)
                # update trading price
                self.trading_price[symbol] = {
                    "cost": ask_price,
                    "quantity": buy_quant,
                }
                self.print_log("🟢 Submit buy order <{}>, quant: {}, limit price: {}".format(
                    symbol, buy_quant, ask_price))
                # update pending buy
                self.update_pending_buy_order(symbol, order_response)

        # sell in regular market hour
        if self.is_regular_market_hour():
            exit_trading, exit_note = self.check_exit(ticker)
            if exit_trading:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = self.get_bid_price_from_quote(quote)
                if bid_price == None:
                    return
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=holding_quantity)
                # update trading price
                self.trading_price[symbol] = {
                    "sell_price": bid_price,
                }
                self.print_log("🔴 Submit sell order <{}>, quant: {}, limit price: {}".format(
                    symbol, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    symbol, order_response, exit_note=exit_note)

    def on_begin(self):
        # prepare tickers for buy
        if self.is_extended_market_hour():
            today = date.today()
            earning_time = None
            # get earning calendars
            if self.is_pre_market_hour():
                earning_time = "bmo"
            elif self.is_after_market_hour():
                earning_time = "amc"
            earnings = EarningCalendar.objects.filter(
                earning_date=today).filter(earning_time=earning_time)
            # update tracking_tickers
            for earning in earnings:
                symbol = earning.symbol
                ticker_id = webullsdk.get_ticker(symbol=symbol)
                ticker = self.get_init_tracking_ticker(symbol, ticker_id)
                self.tracking_tickers[symbol] = ticker
                self.print_log(
                    "Add ticker <{}> to check earning gap!".format(symbol))
        # prepare tickers for sell
        if self.is_regular_market_hour():
            earning_positions = OvernightPosition.objects.filter(
                setup=self.get_setup())
            for position in earning_positions:
                symbol = position.symbol
                ticker_id = position.ticker_id
                ticker = self.get_init_tracking_ticker(symbol, ticker_id)
                self.print_log(
                    "Add ticker <{}> to sell during regular hour!".format(symbol))

    def on_update(self):
        # trading tickers
        for symbol in list(self.tracking_tickers):
            ticker = self.tracking_tickers[symbol]
            # init stats if not
            self.init_tracking_stats_if_not(ticker)
            # do trade
            self.trade(ticker)

    def on_end(self):
        self.trading_end = True

        # save trading logs
        utils.save_trading_log("\n".join(
            self.trading_logs), self.get_tag(), self.trading_hour, date.today())
