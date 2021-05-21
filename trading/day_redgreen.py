# -*- coding: utf-8 -*-

# Momo day trading class

import time
from datetime import datetime, timedelta
from trading.base import TradingBase
from webull_trader.enums import SetupType, AlgorithmType
from sdk import webullsdk
from scripts import utils


class DayTradingRedGreen(TradingBase):

    import pandas as pd

    def get_setup(self):
        return SetupType.DAY_RED_TO_GREEN

    def trade(self, ticker, m1_bars=pd.DataFrame()):

        symbol = ticker['symbol']
        ticker_id = ticker['ticker_id']

        if ticker['pending_buy']:
            self.check_buy_order_filled(ticker)
            return

        if ticker['pending_sell']:
            self.check_sell_order_filled(ticker)
            return

        holding_quantity = ticker['positions']
        # check timeout, skip this ticker if no trade during last OBSERVE_TIMEOUT seconds
        if holding_quantity == 0 and (datetime.now() - ticker['start_time']) >= timedelta(seconds=self.observe_timeout_in_sec):
            print("[{}] Trading <{}>[{}] session timeout!".format(
                utils.get_now(), symbol, ticker_id))
            # remove from monitor
            del self.tracking_tickers[symbol]
            return

        if holding_quantity == 0:
            # fetch 1m bar charts
            if m1_bars.empty:
                m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
            m2_bars = utils.convert_2m_bars(m1_bars)
            if m2_bars.empty:
                return

            if not utils.check_bars_updated(m1_bars):
                print("[{}] <{}>[{}] Charts is not updated, stop trading!".format(
                    utils.get_now(), symbol, ticker_id))
                # remove from monitor
                del self.tracking_tickers[symbol]
                return

            # if not utils.check_bars_volatility(m1_bars):
            #     print("[{}] <{}>[{}] Charts is not volatility, stop trading!".format(
            #         utils.get_now(), symbol, ticker_id))
            #     # remove from monitor
            #     del tracking_tickers[symbol]
            #     return

            # check if last sell time is too short compare current time
            # if ticker['last_sell_time'] != None and (datetime.now() - ticker['last_sell_time']) < timedelta(seconds=TRADE_INTERVAL):
            #     print("[{}] Don't buy <{}>[{}] too quick after sold!".format(
            #         utils.get_now(), symbol, ticker_id))
            #     return

            # calculate and fill ema 9 data
            m2_bars['ema9'] = m2_bars['close'].ewm(span=9, adjust=False).mean()
            current_candle = m2_bars.iloc[-1]
            prev_candle = m2_bars.iloc[-2]

            # current price data
            current_low = current_candle['low']
            prev_low = prev_candle['low']
            current_close = current_candle['close']
            current_vwap = current_candle['vwap']
            current_ema9 = current_candle['ema9']
            current_volume = int(current_candle['volume'])

            # check entry: current price above vwap and ema 9, current low above prev low
            if current_low > current_vwap and current_low > current_ema9 and current_low > prev_low:
                # check first candle make new high
                if current_candle['high'] > prev_candle['high']:
                    quote = webullsdk.get_quote(ticker_id=ticker_id)
                    if quote == None or 'depth' not in quote:
                        return
                    ask_price = float(
                        quote['depth']['ntvAggAskList'][0]['price'])
                    bid_price = float(
                        quote['depth']['ntvAggBidList'][0]['price'])
                    gap = (ask_price - bid_price) / bid_price
                    if gap > self.max_bid_ask_gap_ratio:
                        print("[{}] <{}>[{}] gap too large, ask: {}, bid: {}, stop trading!".format(
                            utils.get_now(), symbol, ticker_id, ask_price, bid_price))
                        # remove from monitor
                        del self.tracking_tickers[symbol]
                        return
                    buy_position_amount = self.get_buy_order_limit(symbol)
                    buy_quant = (int)(buy_position_amount / ask_price)
                    # submit limit order at ask price
                    order_response = webullsdk.buy_limit_order(
                        ticker_id=ticker_id,
                        price=ask_price,
                        quant=buy_quant)
                    print("[{}] Trading <{}>[{}], price: {}, vwap: {}, ema9: {}, volume: {}".format(
                        utils.get_now(), symbol, ticker_id, current_close, current_vwap, round(current_ema9, 3), current_volume))
                    print("[{}] 🟢 Submit buy order <{}>[{}], quant: {}, limit price: {}".format(
                        utils.get_now(), symbol, ticker_id, buy_quant, ask_price))
                    if 'msg' in order_response:
                        print("[{}] {}".format(
                            utils.get_now(), order_response['msg']))
                    else:
                        # mark pending buy
                        self.tracking_tickers[symbol]['pending_buy'] = True
                        self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                        self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                        )
                        # set stop loss at prev low
                        self.tracking_tickers[symbol]['stop_loss'] = prev_low
        else:
            positions = webullsdk.get_positions()
            if positions == None:
                return
            ticker_position = None
            for position in positions:
                if position['ticker']['symbol'] == symbol:
                    ticker_position = position
                    break
            if not ticker_position:
                print("[{}] Finding <{}>[{}] position error!".format(
                    utils.get_now(), symbol, ticker_id))
                return
            # cost = float(ticker_position['cost'])
            # last_price = float(ticker_position['lastPrice'])
            profit_loss_rate = float(
                ticker_position['unrealizedProfitLossRate'])
            self.tracking_tickers[symbol]['last_profit_loss_rate'] = profit_loss_rate
            # due to no stop trailing order in paper account, keep tracking of max P&L rate
            max_profit_loss_rate = self.tracking_tickers[symbol]['max_profit_loss_rate']
            if profit_loss_rate > max_profit_loss_rate:
                self.tracking_tickers[symbol]['max_profit_loss_rate'] = profit_loss_rate
            # quantity = int(ticker_position['position'])
            # print("[{}] Checking <{}>[{}], cost: {}, last: {}, change: {}%".format(
            #     utils.get_now(), symbol, ticker_id, cost, last_price, round(profit_loss_rate * 100, 2)))
            exit_trading = False
            # sell if drawdown 1% from max P&L rate
            # if max_profit_loss_rate - profit_loss_rate >= 0.01:
            #     exit_trading = True
            exit_note = None

            # cancel buy prev low stop loss if hit 1% profit
            if profit_loss_rate >= 0.01:
                self.tracking_tickers[symbol]['stop_loss'] = None

            # stop loss for buy prev low
            if ticker['stop_loss'] and float(ticker_position['lastPrice']) < ticker['stop_loss']:
                exit_note = "Stop loss at {}!".format(
                    ticker_position['lastPrice'])
                exit_trading = True

            # stop loss for stop_loss_ratio
            if not exit_trading and profit_loss_rate <= self.stop_loss_ratio:
                exit_note = "Stop loss for {}%".format(
                    round(profit_loss_rate * 100, 2))
                exit_trading = True

            # check if holding too long without profit
            if not exit_trading and (datetime.now() - ticker['order_filled_time']) >= timedelta(seconds=self.holding_order_timeout_in_sec) and profit_loss_rate < 0.01:
                print("[{}] Holding <{}>[{}] too long!".format(
                    utils.get_now(), symbol, ticker_id))
                exit_note = "Holding too long!"
                exit_trading = True

            if not exit_trading:
                # get 2m bar charts
                m2_bars = utils.convert_2m_bars(
                    webullsdk.get_1m_bars(ticker_id, count=20))

                # get bars error
                if m2_bars.empty:
                    print("[{}] <{}>[{}] Bars data error!".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Bars data error!"
                    exit_trading = True

                # check if momentum is stop
                if not exit_trading and utils.check_bars_current_low_less_than_prev_low(m2_bars):
                    print("[{}] <{}>[{}] Current low price is less than previous low price.".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Current Low < Previous Low."
                    exit_trading = True

                # check if price fixed in last 3 candles
                if not exit_trading and utils.check_bars_price_fixed(m2_bars):
                    print("[{}] <{}>[{}] Price is fixed during last 3 candles.".format(
                        utils.get_now(), symbol, ticker_id))
                    exit_note = "Price fixed during last 3 candles."
                    exit_trading = True

            # exit trading
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
                if 'msg' in order_response:
                    print("[{}] {}".format(
                        utils.get_now(), order_response['msg']))
                else:
                    # mark pending sell
                    self.tracking_tickers[symbol]['pending_sell'] = True
                    self.tracking_tickers[symbol]['pending_order_id'] = order_response['orderId']
                    self.tracking_tickers[symbol]['pending_order_time'] = datetime.now(
                    )
                    self.tracking_tickers[symbol]['exit_note'] = exit_note
                # update trading stats
                if symbol not in self.trading_stats:
                    self.trading_stats[symbol] = {
                        "trades": 0,
                        "win_trades": 0,
                        "lose_trades": 0,
                        "continue_lose_trades": 0,
                        "last_trade_time": None,
                    }
                self.trading_stats[symbol]['trades'] += 1
                self.trading_stats[symbol]['last_trade_time'] = datetime.now()
                if profit_loss_rate > 0:
                    self.trading_stats[symbol]['win_trades'] += 1
                    self.trading_stats[symbol]['continue_lose_trades'] = 0
                else:
                    self.trading_stats[symbol]['lose_trades'] += 1
                    self.trading_stats[symbol]['continue_lose_trades'] += 1

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

        # main loop
        while utils.is_regular_market_hour():
            # trading tickers
            for symbol in list(self.tracking_tickers):
                ticker = self.tracking_tickers[symbol]
                # do trade
                self.trade(ticker)

            # find trading ticker in top gainers
            top_gainers = []
            if utils.is_regular_market_hour():
                top_gainers = webullsdk.get_top_gainers()
            elif utils.is_pre_market_hour():
                top_gainers = webullsdk.get_pre_market_gainers()
            elif utils.is_after_market_hour():
                top_gainers = webullsdk.get_after_market_gainers()

            # print("[{}] Scanning top gainers [{}]...".format(
            #     utils.get_now(), ', '.join([gainer['symbol'] for gainer in top_10_gainers])))
            for gainer in top_gainers:
                symbol = gainer["symbol"]
                # check if ticker already in monitor
                if symbol in self.tracking_tickers:
                    continue
                ticker_id = gainer["ticker_id"]
                # print("[{}] Scanning <{}>[{}]...".format(
                #     utils.get_now(), symbol, ticker_id))
                change_percentage = gainer["change_percentage"]
                # check gap change
                if change_percentage >= self.min_surge_change_ratio and self.check_if_track_symbol(symbol):
                    m1_bars = webullsdk.get_1m_bars(ticker_id, count=60)
                    m2_bars = utils.convert_2m_bars(m1_bars)
                    if m2_bars.empty:
                        continue
                    # use latest formed candle
                    latest_candle = m2_bars.iloc[-2]
                    if utils.check_bars_updated(m2_bars):
                        latest_close = latest_candle["close"]
                        latest_vwap = latest_candle["vwap"]
                        volume = int(latest_candle["volume"])
                        # check if trasaction amount meets requirement
                        if latest_close * volume >= self.min_surge_amount and volume >= self.min_surge_volume and latest_close >= latest_vwap:
                            # found trading ticker
                            ticker = {
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
                            }
                            self.tracking_tickers[symbol] = ticker
                            print("[{}] Found <{}>[{}] to trade!".format(
                                utils.get_now(), symbol, ticker_id))
                            # do trade
                            self.trade(ticker, m1_bars=m1_bars)

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
                self.complete_order(ticker)

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

        # webullsdk.logout()
        # print("[{}] Webull logged out".format(utils.get_now()))


def start():
    from scripts import utils
    from trading.day_redgreen import DayTradingRedGreen

    paper = utils.check_paper()
    daytrading = DayTradingRedGreen(paper=paper)
    daytrading.start()


if __name__ == "django.core.management.commands.shell":
    start()
