# -*- coding: utf-8 -*-

# Momo day trading class

import time
from datetime import datetime, timedelta
from trading.trading_base import TradingBase
from webull_trader.enums import SetupType, AlgorithmType
from webull_trader.models import HistoricalTopGainer, HistoricalTopLoser
from sdk import webullsdk
from scripts import utils


class DayTradingRedGreen(TradingBase):

    def get_setup(self):
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']
        prev_day_close = ticker['prev_close']
        prev_day_high = ticker['prev_high']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']

        # fetch 1m bar charts
        m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
        m2_bars = utils.convert_2m_bars(m1_bars)
        if m2_bars.empty:
            return

        current_candle = m2_bars.iloc[-1]
        prev_candle = m2_bars.iloc[-2]
        preprev_candle = m2_bars.iloc[-3]

        # current price data
        current_close = current_candle['close']
        current_high = current_candle['high']
        current_low = current_candle['low']
        prev_low = prev_candle['low']
        preprev_volume = preprev_candle['volume']
        current_volume = int(current_candle['volume'])

        if holding_quantity == 0:

            # check entry, current price above prev day close
            if current_low >= prev_day_close and prev_low <= prev_day_close:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None or 'depth' not in quote:
                    return
                ask_price = float(
                    quote['depth']['ntvAggAskList'][0]['price'])
                buy_position_amount = self.get_buy_order_limit(symbol)
                buy_quant = (int)(buy_position_amount / ask_price)
                # submit limit order at ask price
                order_response = webullsdk.buy_limit_order(
                    ticker_id=ticker_id,
                    price=ask_price,
                    quant=buy_quant)
                print("[{}] Trading <{}>[{}], price: {}, volume: {}".format(
                    utils.get_now(), symbol, ticker_id, current_close, current_volume))
                print("[{}] 🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                    utils.get_now(), symbol, ticker_id, buy_quant, ask_price))
                # update pending buy
                self.update_pending_buy_order(
                    symbol, order_response, stop_loss=prev_day_close)
        else:
            ticker_position = self.get_position(ticker)
            if not ticker_position:
                print("[{}] Finding <{}>[{}] position error!".format(
                    utils.get_now(), symbol, ticker_id))
                return
            # profit loss rate
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate
            # check if exit trading
            exit_trading = False
            last_price = ticker_position['lastPrice']
            # check stop loss, prev day close
            if current_high < ticker['stop_loss']:
                exit_note = "Stop loss at {}!".format(last_price)
                exit_trading = True
            # check taking profit, current price above prev day high
            if last_price >= prev_day_high:
                exit_note = "Take profit at {}!".format(last_price)
                exit_trading = True
            if exit_trading:
                quote = webullsdk.get_quote(ticker_id=ticker_id)
                if quote == None:
                    return
                bid_price = float(
                    quote['depth']['ntvAggBidList'][0]['price'])
                order_response = webullsdk.sell_limit_order(
                    ticker_id=ticker_id,
                    price=bid_price,
                    quant=holding_quantity)
                print("[{}] 📈 Exit trading <{}>[{}] P&L: {}%".format(
                    utils.get_now(), symbol, ticker_id, round(profit_loss_rate * 100, 2)))
                print("[{}] 🔴 Submit sell order <{}>[{}], quant: {}, limit price: {}".format(
                    utils.get_now(), symbol, ticker_id, holding_quantity, bid_price))
                # update pending sell
                self.update_pending_sell_order(
                    symbol, order_response, exit_note=exit_note)

    def print_algo_name(self):
        print("[{}] {}".format(utils.get_now(),
              AlgorithmType.tostr(AlgorithmType.DAY_RED_TO_GREEN)))

    def start(self):

        if not self.load_settings():
            print("[{}] Cannot find trading settings, quit!".format(
                utils.get_now()))
            return

        print("[{}] Trading started...".format(utils.get_now()))

        self.print_algo_name()

        while not utils.is_regular_market_hour():
            print("[{}] Waiting for market hour...".format(utils.get_now()))
            time.sleep(10)

        # login
        if not webullsdk.login(paper=self.paper):
            print("[{}] Webull login failed, quit!".format(
                utils.get_now()))
            return
        print("[{}] Webull logged in".format(utils.get_now()))
        last_login_refresh_time = datetime.now()

        today = datetime.today().date()
        last_market_day = today - timedelta(days=1)
        if today.weekday() == 0:
            # if monday
            last_market_day = today - timedelta(days=3)

        # hist top gainers
        top_gainers = HistoricalTopGainer.objects.filter(date=last_market_day)
        # update tracking_tickers
        for gainer in top_gainers:
            quote = webullsdk.get_quote(ticker_id=gainer.ticker_id)
            # weak open
            if float(quote['open']) <= gainer.price:
                key_stat = utils.get_hist_key_stat(
                    gainer.symbol, last_market_day)
                ticker = self.get_init_tracking_ticker(
                    gainer.symbol, gainer.ticker_id, prev_close=gainer.price, prev_high=key_stat.high)
                self.tracking_tickers[gainer.symbol] = ticker
                print("[{}] Add gainer <{}>[{}] to trade!".format(
                    utils.get_now(), gainer.symbol, gainer.ticker_id))
        # hist top losers
        top_losers = HistoricalTopLoser.objects.filter(date=last_market_day)
        # update tracking_tickers
        for loser in top_losers:
            quote = webullsdk.get_quote(ticker_id=loser.ticker_id)
            # weak open
            if float(quote['open']) <= loser.price:
                key_stat = utils.get_hist_key_stat(
                    loser.symbol, last_market_day)
                ticker = self.get_init_tracking_ticker(
                    loser.symbol, loser.ticker_id, prev_close=loser.price, prev_high=key_stat.high)
                self.tracking_tickers[loser.symbol] = ticker
                print("[{}] Add loser <{}>[{}] to trade!".format(
                    utils.get_now(), loser.symbol, loser.ticker_id))

        # main loop
        while utils.is_regular_market_hour() and datetime.now().hour <= 11:
            # trading tickers
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                # do trade
                self.trade(ticker)

            # refresh login
            if (datetime.now() - last_login_refresh_time) >= timedelta(minutes=self.refresh_login_interval_in_min):
                webullsdk.login(paper=self.paper)
                print("[{}] Refresh webull login".format(utils.get_now()))
                last_login_refresh_time = datetime.now()

            # at least slepp 1 sec
            time.sleep(1)

        # check if still holding any positions before exit
        while len(list(self.tracking_tickers)) > 0:
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                self.clear_position(ticker)

            # at least slepp 1 sec
            time.sleep(1)

        print("[{}] Trading ended!".format(utils.get_now()))

        # output today's proft loss
        portfolio = webullsdk.get_portfolio()
        day_profit_loss = "-"
        if "dayProfitLoss" in portfolio:
            day_profit_loss = portfolio['dayProfitLoss']
        print("[{}] Today's P&L: {}".format(
            utils.get_now(), day_profit_loss))


def start():
    from scripts import utils
    from trading.day_redgreen import DayTradingRedGreen

    paper = utils.check_paper()
    daytrading = DayTradingRedGreen(paper=paper)
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()
