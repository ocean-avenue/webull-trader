from datetime import date
from common.utils import get_now
from common.enums import AlgorithmType, UNKNOWN, TradingHourType
from webull_trader.models import TradingLog, TradingSettings

_algo_tag = UNKNOWN
_trading_logs = []


def log(text: str):
    global _trading_logs
    log_record = "[{}] {}".format(get_now(), text)
    _trading_logs.append(log_record)
    # output
    print(log_record)


def write(trading_hour: TradingHourType, date: date):
    global _algo_tag
    global _trading_logs
    if len(_trading_logs) == 0:
        return
    if _algo_tag == UNKNOWN:
        settings: TradingSettings = TradingSettings.objects.first()
        _algo_tag = AlgorithmType.totag(settings.algo_type)
    log_obj = TradingLog.objects.filter(date=date).filter(
        tag=_algo_tag).filter(trading_hour=trading_hour).first()
    if log_obj == None:
        log_obj = TradingLog(
            date=date,
            tag=_algo_tag,
            trading_hour=trading_hour,
        )
    log_text = "\n".join(_trading_logs)
    if log_obj.log_text == None:
        log_obj.log_text = log_text
    else:
        log_obj.log_text = log_obj.log_text + log_text
    log_obj.log_text += "\n"
    log_obj.save()
    # reset _trading_logs
    _trading_logs = []


def log_level2(quote):
    if quote:
        symbol = "(TBA)"
        if "symbol" in quote:
            symbol = quote["symbol"]
        elif "disSymbol" in quote:
            symbol = quote["disSymbol"]
        # level 1
        ask_list = []
        bid_list = []
        if 'askList' in quote and 'bidList' in quote:
            ask_list = quote['askList']
            bid_list = quote['bidList']
        # level 2
        if 'depth' in quote and 'ntvAggAskList' in quote['depth'] and 'ntvAggBidList' in quote['depth']:
            ask_list = quote['depth']['ntvAggAskList']
            bid_list = quote['depth']['ntvAggBidList']
        # print log
        log("Order book for <{}>:".format(symbol))
        depth = max(len(ask_list), len(bid_list))
        for i in range(0, depth):
            bid_record = "{:<10} {:>10}".format("*", "*")
            if i < len(bid_list):
                bid_record = "{:<10} {:>10}".format(
                    bid_list[i]['volume'], bid_list[i]['price'])
            ask_record = "{:<10} {:>10}".format("*", "*")
            if i < len(ask_list):
                ask_record = "{:<10} {:>10}".format(
                    ask_list[i]['price'], ask_list[i]['volume'])
            log("{} - {}".format(bid_record, ask_record))
