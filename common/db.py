from typing import List, Optional
from django.db.models.query import QuerySet
import pytz
from django.conf import settings
from datetime import datetime, date
from common import enums, utils, constants
from sdk import webullsdk
from logger import exception_logger
from webull_trader.models import DayPosition, DayTrade, HistoricalDailyBar, HistoricalDayTradePerformance, HistoricalKeyStatistics, HistoricalMarketStatistics, HistoricalMinuteBar, HistoricalTopGainer, \
    HistoricalTopLoser, SwingHistoricalDailyBar, TradingSettings, TradingSymbols, WebullAccountStatistics, WebullCredentials, WebullNews, WebullOrder


def get_or_create_trading_settings() -> TradingSettings:
    trading_settings = TradingSettings.objects.first()
    if not trading_settings:
        trading_settings = TradingSettings(
            paper=True,
            algo_type=enums.AlgorithmType.DAY_BREAKOUT_20,
            order_amount_limit=1000.0,
            extended_order_amount_limit=1000.0,
            target_profit_ratio=0.02,
            stop_loss_ratio=-0.01,
            day_free_float_limit_in_million=-1.0,  # all free float
            day_turnover_rate_limit_percentage=-1.0,  # all turnover rate
            day_sectors_limit='',  # all sectors
            swing_position_amount_limit=1000.0,
            day_trade_usable_cash_threshold=10000.0,
        )
        trading_settings.save()
    return trading_settings


def get_trading_symbols():
    trading_symbols = TradingSymbols.objects.first()
    if trading_symbols:
        symbol_text = trading_symbols.symbols
        if len(symbol_text) == 0:
            return []
        return symbol_text.upper().split("\r\n")
    return []


def get_hist_key_stat(symbol: str, date: date) -> HistoricalKeyStatistics:
    key_statistics = HistoricalKeyStatistics.objects.filter(
        symbol=symbol).filter(date=date).first()
    return key_statistics


def get_hist_market_stat(date: date) -> HistoricalMarketStatistics:
    market_statistics = HistoricalMarketStatistics.objects.filter(
        date=date).first()
    return market_statistics


def get_hist_top_gainer(symbol: str, date: date) -> HistoricalTopGainer:
    top_gainer = HistoricalTopGainer.objects.filter(
        symbol=symbol).filter(date=date).first()
    return top_gainer


def get_hist_top_loser(symbol: str, date: date) -> HistoricalTopLoser:
    top_loser = HistoricalTopLoser.objects.filter(
        symbol=symbol).filter(date=date).first()
    return top_loser


def save_webull_credentials(cred_data: dict, paper: bool = True):
    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        credentials = WebullCredentials(
            cred=cred_data,
            paper=paper,
        )
    else:
        credentials.cred = cred_data
    credentials.save()


def save_webull_account(acc_data: dict, paper: bool = True, day: date = None):
    if day == None:
        day = date.today()
    print("[{}] Importing daily account status ({})...".format(
        utils.get_now(), day.strftime("%Y-%m-%d")))
    if paper:
        if "accountMembers" in acc_data:
            account_members = acc_data['accountMembers']
            day_profit_loss = 0
            min_usable_cash = 0
            for account_member in account_members:
                if account_member['key'] == 'dayProfitLoss':
                    day_profit_loss = float(account_member['value'])
                if account_member['key'] == 'usableCash':
                    min_usable_cash = float(account_member['value'])
            acc_stat = WebullAccountStatistics.objects.filter(
                date=day).first()
            if not acc_stat:
                acc_stat = WebullAccountStatistics(
                    date=day,
                    min_usable_cash=min_usable_cash,
                )
            acc_stat.net_liquidation = float(acc_data['netLiquidation'])
            acc_stat.total_profit_loss = float(acc_data['totalProfitLoss'])
            acc_stat.total_profit_loss_rate = float(
                acc_data['totalProfitLossRate'])
            acc_stat.day_profit_loss = day_profit_loss
            acc_stat.save()
    else:
        if "accountMembers" in acc_data:
            account_members = acc_data['accountMembers']
            min_usable_cash = 0
            for account_member in account_members:
                if account_member['key'] == 'cashBalance':
                    min_usable_cash = float(account_member['value'])
            acc_stat = WebullAccountStatistics.objects.filter(
                date=day).first()
            if not acc_stat:
                acc_stat = WebullAccountStatistics(
                    date=day,
                    min_usable_cash=min_usable_cash,
                )
            acc_stat.net_liquidation = float(acc_data['netLiquidation'])
            # get day's P&L
            daily_pl = webullsdk.get_daily_profitloss()
            day_profit_loss = 0
            if len(daily_pl) > 0:
                day_pl = daily_pl[-1]
                if day_pl['periodName'] == day.strftime("%Y-%m-%d"):
                    day_profit_loss = float(day_pl['profitLoss'])
            acc_stat.total_profit_loss = acc_stat.total_profit_loss or 0
            acc_stat.total_profit_loss_rate = acc_stat.total_profit_loss_rate or 0
            acc_stat.day_profit_loss = day_profit_loss
            acc_stat.save()
            # update total profit loss
            all_acc_stats = WebullAccountStatistics.objects.all()
            total_profit_loss = 0
            for acc in all_acc_stats:
                total_profit_loss += acc.day_profit_loss
            acc_stat.total_profit_loss = total_profit_loss
            if (acc_stat.net_liquidation - acc_stat.total_profit_loss) != 0:
                acc_stat.total_profit_loss_rate = acc_stat.total_profit_loss / \
                    (acc_stat.net_liquidation - acc_stat.total_profit_loss)
            acc_stat.save()


def _order_action_fmt(action_str: str) -> enums.ActionType:
    action = enums.ActionType.BUY
    if action_str == "SELL":
        action = enums.ActionType.SELL
    return action


def _order_type_fmt(type_str: str) -> enums.OrderType:
    order_type = enums.OrderType.LMT
    if type_str == "MKT":
        order_type = enums.OrderType.MKT
    elif type_str == "STP":
        order_type = enums.OrderType.STP
    elif type_str == "STP LMT":
        order_type = enums.OrderType.STP_LMT
    elif type_str == "STP TRAIL":
        order_type = enums.OrderType.STP_TRAIL
    return order_type


def _order_time_fmt(order_time_str: str) -> datetime:
    time_fmt = "%m/%d/%Y %H:%M:%S EDT"
    if "EST" in order_time_str:
        time_fmt = "%m/%d/%Y %H:%M:%S EST"
    return pytz.timezone(settings.TIME_ZONE).localize(datetime.strptime(order_time_str, time_fmt))


def _time_in_force_fmt(time_in_force_str: str) -> enums.TimeInForceType:
    time_in_force = enums.TimeInForceType.GTC
    if time_in_force_str == "DAY":
        time_in_force = enums.TimeInForceType.DAY
    elif time_in_force_str == "IOC":
        time_in_force = enums.TimeInForceType.IOC
    return time_in_force


def save_webull_order(order_data: dict, paper: bool = True) -> WebullOrder:
    avg_price = 0.0
    price = 0.0
    filled_time = None
    placed_time = None
    # create_time = None
    if paper:
        order_id = str(order_data['orderId'])
        if "symbol" in order_data['ticker']:
            symbol = order_data['ticker']['symbol']
        else:
            symbol = order_data['ticker']['disSymbol']
        ticker_id = str(order_data['ticker']['tickerId'])
        action = _order_action_fmt(order_data['action'])
        status = order_data['statusStr']
        order_type = _order_type_fmt(order_data['orderType'])
        total_quantity = int(order_data['totalQuantity'])
        filled_quantity = int(order_data['filledQuantity'])
        if 'avgFilledPrice' in order_data:
            avg_price = float(order_data['avgFilledPrice'])
            price = avg_price
        if 'lmtPrice' in order_data:
            price = float(order_data['lmtPrice'])
        if 'filledTime' in order_data:
            filled_time = _order_time_fmt(order_data['filledTime'])
        if 'placedTime' in order_data:
            placed_time = _order_time_fmt(order_data['placedTime'])
            # create_time = order_data['placedTime']
        time_in_force = _time_in_force_fmt(order_data['timeInForce'])
    else:
        order_obj = order_data['orders'][0]
        order_id = str(order_obj['orderId'])
        if "symbol" in order_obj['ticker']:
            symbol = order_obj['ticker']['symbol']
        else:
            symbol = order_obj['ticker']['disSymbol']
        ticker_id = str(order_obj['ticker']['tickerId'])
        action = _order_action_fmt(order_obj['action'])
        status = order_obj['statusStr']
        order_type = _order_type_fmt(order_obj['orderType'])
        total_quantity = int(order_obj['totalQuantity'])
        filled_quantity = int(order_obj['filledQuantity'])
        if 'avgFilledPrice' in order_obj:
            avg_price = float(order_obj['avgFilledPrice'])
            price = avg_price
        if 'lmtPrice' in order_obj:
            price = float(order_obj['lmtPrice'])
        if 'auxPrice' in order_obj:  # for stop order
            price = float(order_obj['auxPrice'])
        if 'filledTime' in order_obj:
            filled_time = _order_time_fmt(order_obj['filledTime'])
        if 'createTime' in order_obj:
            placed_time = _order_time_fmt(order_obj['createTime'])
            # create_time = order_obj['createTime']
        time_in_force = _time_in_force_fmt(order_obj['timeInForce'])

    order = WebullOrder.objects.filter(order_id=order_id).first()
    # if order:
    #     print("[{}] Updating order <{}> {} ({})...".format(
    #         utils.get_now(), symbol, order_id, create_time))
    # else:
    #     print("[{}] Importing order <{}> {} ({})...".format(
    #         utils.get_now(), symbol, order_id, create_time))
    if order:
        order.ticker_id = ticker_id
        order.symbol = symbol
        order.action = action
        order.status = status
        order.total_quantity = total_quantity
        order.filled_quantity = filled_quantity
        order.price = price
        order.avg_price = avg_price
        order.order_type = order_type
        order.filled_time = filled_time
        order.placed_time = placed_time
        order.time_in_force = time_in_force
        order.paper = paper
    else:
        order = WebullOrder(
            order_id=order_id,
            ticker_id=ticker_id,
            symbol=symbol,
            action=action,
            status=status,
            total_quantity=total_quantity,
            filled_quantity=filled_quantity,
            price=price,
            avg_price=avg_price,
            order_type=order_type,
            filled_time=filled_time,
            placed_time=placed_time,
            time_in_force=time_in_force,
            paper=paper,
        )
    order.save()
    return order


def save_webull_order_backtest(order_data: dict, setup: enums.SetupType, note: str) -> WebullOrder:
    order = WebullOrder(
        order_id=str(order_data['orderId']),
        ticker_id=str(order_data['ticker']['tickerId']),
        symbol=order_data['ticker']['symbol'],
        action=order_data['action'],
        status=order_data['statusStr'],
        total_quantity=int(order_data['totalQuantity']),
        filled_quantity=int(order_data['filledQuantity']),
        price=float(order_data['lmtPrice']),
        avg_price=float(order_data['avgFilledPrice']),
        order_type=order_data['orderType'],
        filled_time=order_data['filledTime'],
        placed_time=order_data['placedTime'],
        time_in_force=order_data['timeInForce'],
        paper=True,
        setup=setup,
        note=note,
    )
    order.save()
    return order


def save_webull_min_usable_cash(usable_cash: float, day: Optional[date] = None):
    if not day:
        day = date.today()
    acc_stat = WebullAccountStatistics.objects.filter(date=day).first()
    if not acc_stat:
        acc_stat = WebullAccountStatistics(
            date=day,
            net_liquidation=0.0,
            total_profit_loss=0.0,
            total_profit_loss_rate=0.0,
            day_profit_loss=0.0,
        )
    if usable_cash < acc_stat.min_usable_cash or acc_stat.min_usable_cash == 0.0:
        acc_stat.min_usable_cash = usable_cash
        acc_stat.save()


def add_day_position(symbol: str, ticker_id: str, order_id: str, setup: enums.SetupType,
                     cost: float, quant: int, buy_time: datetime, units: int = 1, target_units: int = 4,
                     add_unit_price: float = constants.MAX_SECURITY_PRICE, stop_loss_price: float = 0.0,
                     require_adjustment: bool = True) -> Optional[DayPosition]:
    try:
        position = DayPosition(
            symbol=symbol,
            ticker_id=ticker_id,
            order_ids=order_id,
            total_cost=round(cost * quant, 2),
            quantity=quant,
            units=units,
            target_units=target_units,
            add_unit_price=add_unit_price,
            stop_loss_price=stop_loss_price,
            buy_date=buy_time.date(),
            buy_time=buy_time,
            setup=setup,
            require_adjustment=require_adjustment,
        )
        position.save()
        return position
    except Exception as e:
        exception_logger.log(str(e),
                             f"symbol: <{symbol}>, ticker_id: {ticker_id}, order_id: {order_id}, setup: {setup}, cost: {cost}, quant: {quant}, buy_time: {buy_time}")
        return None


def add_day_trade(symbol: str, ticker_id: str, position: DayPosition, order_id: str, sell_price: float, sell_time: datetime, require_adjustment: bool = True) -> Optional[DayTrade]:
    trade = DayTrade(
        symbol=symbol,
        ticker_id=ticker_id,
        order_ids=f"{position.order_ids},{order_id}",
        total_cost=position.total_cost,
        total_sold=round(sell_price * position.quantity, 2),
        quantity=position.quantity,
        units=position.units,
        buy_date=position.buy_date,
        buy_time=position.buy_time,
        sell_date=sell_time.date(),
        sell_time=sell_time,
        setup=position.setup,
        require_adjustment=require_adjustment,
    )
    trade.save()
    return trade


def save_webull_news_list(news_list: List[dict], symbol: str, date: date):
    print("[{}] Importing news for {}...".format(utils.get_now(), symbol))
    for news_data in news_list:
        save_webull_news(news_data, symbol, date)


def save_webull_news(news_data: dict, symbol: str, date: date):
    news: Optional[WebullNews] = WebullNews.objects.filter(
        news_id=news_data['id'], symbol=symbol, date=date).first()
    if not news:
        news = WebullNews(
            news_id=utils.get_attr(news_data, 'id'),
            symbol=symbol,
            title=utils.get_attr(news_data, 'title'),
            source_name=utils.get_attr(news_data, 'sourceName'),
            collect_source=utils.get_attr(news_data, 'collectSource'),
            news_time=utils.get_attr(news_data, 'newsTime'),
            summary=utils.get_attr(news_data, 'summary'),
            news_url=utils.get_attr(news_data, 'newsUrl'),
            date=date,
        )
        news.save()


def save_hist_key_statistics(quote_data: dict, date: date):
    if 'symbol' not in quote_data:
        return
    symbol = quote_data['symbol']
    print("[{}] Importing key statistics for {}...".format(
        utils.get_now(), symbol))
    key_statistics = get_hist_key_stat(symbol, date)
    if not key_statistics:
        turnover_rate = None
        if 'turnoverRate' in quote_data and quote_data['turnoverRate'] != "-" and quote_data['turnoverRate'] != None:
            turnover_rate = float(quote_data['turnoverRate'])
        vibrate_ratio = None
        if 'vibrateRatio' in quote_data and quote_data['vibrateRatio'] != "-" and quote_data['vibrateRatio'] != None:
            vibrate_ratio = float(quote_data['vibrateRatio'])
        total_shares = None
        if 'totalShares' in quote_data and quote_data['totalShares'] != "-" and quote_data['totalShares'] != None:
            total_shares = float(quote_data['totalShares'])
        outstanding_shares = None
        if 'outstandingShares' in quote_data and quote_data['outstandingShares'] != "-" and quote_data['outstandingShares'] != None:
            outstanding_shares = float(quote_data['outstandingShares'])
        short_float = None
        if 'shortFloat' in quote_data and quote_data['shortFloat'] != "-" and quote_data['shortFloat'] != None:
            short_float = float(quote_data['shortFloat'])
        key_statistics = HistoricalKeyStatistics(
            symbol=symbol,
            open=utils.get_attr_to_float(quote_data, 'open'),
            high=utils.get_attr_to_float(quote_data, 'high'),
            low=utils.get_attr_to_float(quote_data, 'low'),
            close=utils.get_attr_to_float(quote_data, 'close'),
            change=utils.get_attr_to_float(quote_data, 'change'),
            change_ratio=utils.get_attr_to_float(quote_data, 'changeRatio'),
            market_value=utils.get_attr_to_float(quote_data, 'marketValue'),
            volume=utils.get_attr_to_float(quote_data, 'volume'),
            turnover_rate=turnover_rate,
            vibrate_ratio=vibrate_ratio,
            avg_vol_10d=utils.get_attr_to_float(quote_data, 'avgVol10D'),
            avg_vol_3m=utils.get_attr_to_float(quote_data, 'avgVol3M'),
            pe=utils.get_attr_to_float_or_none(quote_data, 'pe'),
            forward_pe=utils.get_attr_to_float_or_none(
                quote_data, 'forwardPe'),
            pe_ttm=utils.get_attr_to_float_or_none(quote_data, 'peTtm'),
            eps=utils.get_attr_to_float_or_none(quote_data, 'eps'),
            eps_ttm=utils.get_attr_to_float_or_none(quote_data, 'epsTtm'),
            pb=utils.get_attr_to_float_or_none(quote_data, 'pb'),
            ps=utils.get_attr_to_float_or_none(quote_data, 'ps'),
            bps=utils.get_attr_to_float_or_none(quote_data, 'bps'),
            short_float=short_float,
            total_shares=total_shares,
            outstanding_shares=outstanding_shares,
            fifty_two_wk_high=utils.get_attr_to_float(
                quote_data, 'fiftyTwoWkHigh'),
            fifty_two_wk_low=utils.get_attr_to_float(
                quote_data, 'fiftyTwoWkLow'),
            latest_earnings_date=utils.get_attr(
                quote_data, 'latestEarningsDate'),
            estimate_earnings_date=utils.get_attr(
                quote_data, 'estimateEarningsDate'),
            date=date,
        )
        key_statistics.save()


def save_hist_market_statistics(market_data: dict, date: date):
    market_statistics = get_hist_market_stat(date)
    if not market_statistics:
        market_statistics = HistoricalMarketStatistics(date=date)
    market_statistics.pre_gainer_change = market_data['pre_gainer_change']
    market_statistics.top_gainer_change = market_data['top_gainer_change']
    market_statistics.after_gainer_change = market_data['after_gainer_change']
    market_statistics.pre_loser_change = market_data['pre_loser_change']
    market_statistics.top_loser_change = market_data['top_loser_change']
    market_statistics.after_loser_change = market_data['after_loser_change']
    market_statistics.save()


def save_hist_top_gainer(gainer_data: dict, date: date):
    symbol = gainer_data['symbol']
    print("[{}] Importing top gainer for {}...".format(
        utils.get_now(), symbol))
    top_gainer = get_hist_top_gainer(symbol, date)
    if not top_gainer:
        top_gainer = HistoricalTopGainer(
            symbol=symbol,
            date=date,
        )
    top_gainer.ticker_id = gainer_data['ticker_id']
    top_gainer.change = gainer_data['change']
    top_gainer.change_percentage = gainer_data['change_percentage']
    top_gainer.price = gainer_data['close']
    top_gainer.save()


def save_hist_top_loser(loser_data: dict, date: date):
    symbol = loser_data['symbol']
    print("[{}] Importing top loser for {}...".format(
        utils.get_now(), symbol))
    top_loser = get_hist_top_loser(symbol, date)
    if not top_loser:
        top_loser = HistoricalTopLoser(
            symbol=symbol,
            date=date,
        )
    top_loser.ticker_id = loser_data['ticker_id']
    top_loser.change = loser_data['change']
    top_loser.change_percentage = loser_data['change_percentage']
    top_loser.price = loser_data['close']
    top_loser.save()


def get_hist_minute_bar(symbol: str, time: datetime) -> Optional[HistoricalMinuteBar]:
    return HistoricalMinuteBar.objects.filter(symbol=symbol).filter(
        time__year=str(time.year), time__month=str(time.month), time__day=str(time.day), time__hour=str(time.hour), time__minute=str(time.minute)).first()


def get_hist_day_perf(day: date) -> HistoricalDayTradePerformance:
    return HistoricalDayTradePerformance.objects.filter(date=day).first()


def save_hist_minute_bar_list(bar_list: List[dict]):
    if len(bar_list) > 0:
        print("[{}] Importing minute bar for {}...".format(
            utils.get_now(), bar_list[0]['symbol']))
        for bar_data in bar_list:
            save_hist_minute_bar(bar_data)


def save_hist_minute_bar(bar_data: dict):
    bar = HistoricalMinuteBar.objects.filter(
        symbol=bar_data['symbol'], time=bar_data['time']).first()
    if not bar:
        bar = HistoricalMinuteBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            time=bar_data['time'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
            vwap=bar_data['vwap'],
        )
        bar.save()


def save_hist_daily_bar_list(bar_list: List[dict]):
    if len(bar_list) > 0:
        print("[{}] Importing daily bar for {}...".format(
            utils.get_now(), bar_list[0]['symbol']))
        for bar_data in bar_list:
            save_hist_daily_bar(bar_data)


def save_hist_daily_bar(bar_data: dict):
    bar = HistoricalDailyBar.objects.filter(
        symbol=bar_data['symbol'], date=bar_data['date']).first()
    if not bar:
        bar = HistoricalDailyBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
        )
        bar.save()


def save_swing_hist_daily_bar_list(bar_list: List[dict]):
    print("[{}] Importing swing daily bar for {}...".format(
        utils.get_now(), bar_list[0]['symbol']))
    for bar_data in bar_list:
        save_swing_hist_daily_bar(bar_data)


def save_swing_hist_daily_bar(bar_data: dict):
    bar = SwingHistoricalDailyBar.objects.filter(
        symbol=bar_data['symbol'], date=bar_data['date']).first()
    if not bar:
        bar = SwingHistoricalDailyBar(
            symbol=bar_data['symbol'],
            date=bar_data['date'],
            open=bar_data['open'],
            high=bar_data['high'],
            low=bar_data['low'],
            close=bar_data['close'],
            volume=bar_data['volume'],
            rsi_10=bar_data['rsi_10'],
            sma_55=bar_data['sma_55'],
            sma_120=bar_data['sma_120'],
        )
        bar.save()
