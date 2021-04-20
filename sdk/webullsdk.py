import requests
import json
import time
from webull import webull, paper_webull
import pandas as pd
from scripts import utils
from sdk.config import WEBULL_AFTER_MARKET_LOSERS_URL, WEBULL_PRE_MARKET_GAINERS_URL, WEBULL_AFTER_MARKET_GAINERS_URL, WEBULL_QUOTE_1M_CHARTS_URL, WEBULL_TOP_GAINERS_URL, WEBULL_TOP_LOSERS_URL

wb_instance = None


def login(paper=True):
    global wb_instance
    if paper:
        wb_instance = paper_webull()
    else:
        wb_instance = webull()
    credential_file = 'credentials/webull_live.json'
    if paper:
        credential_file = 'credentials/webull_paper.json'
    input = open(credential_file, 'r')
    credential_data = json.load(input)
    input.close()

    wb_instance._refresh_token = credential_data['refreshToken']
    wb_instance._access_token = credential_data['accessToken']
    wb_instance._token_expire = credential_data['tokenExpireTime']
    wb_instance._uuid = credential_data['uuid']

    n_data = wb_instance.refresh_login()

    credential_data['refreshToken'] = n_data['refreshToken']
    credential_data['accessToken'] = n_data['accessToken']
    credential_data['tokenExpireTime'] = n_data['tokenExpireTime']

    output = open(credential_file, 'w')
    json.dump(credential_data, output)
    output.close()

    wb_instance.get_account_id()


def logout():
    wb_instance.logout()


def get_account():
    return wb_instance.get_account()


# {'totalMarketValue': '0.00', 'usableCash': '4876.63', 'dayProfitLoss': '-133.15'}

def get_portfolio():
    return wb_instance.get_portfolio()


def get_trade_token(password=''):
    return wb_instance.get_trade_token(password=password)

# {
#    "tickerId":925348770,
#    "exchangeId":10,
#    "type":2,
#    "secType":[
#       61
#    ],
#    "regionId":6,
#    "regionCode":"US",
#    "currencyId":247,
#    "name":"American Virtual Cloud Technologies",
#    "symbol":"AVCT",
#    "disSymbol":"AVCT",
#    "disExchangeCode":"NASDAQ",
#    "exchangeCode":"NAS",
#    "listStatus":1,
#    "template":"stock",
#    "derivativeSupport":1,
#    "tradeTime":"2021-04-07T23:59:29.374+0000",
#    "status":"A",
#    "close":"5.81",
#    "change":"-0.23",
#    "changeRatio":"-0.0381",
#    "pPrice":"8.65",
#    "pChange":"2.84",
#    "pChRatio":"0.4888",
#    "marketValue":"114765284.41",
#    "volume":"221671",
#    "turnoverRate":"0.0112",
#    "timeZone":"America/New_York",
#    "tzName":"EDT",
#    "preClose":"6.04",
#    "open":"5.99",
#    "high":"5.99",
#    "low":"5.70",
#    "vibrateRatio":"0.0480",
#    "avgVol10D":"31626",
#    "avgVol3M":"55179",
#    "negMarketValue":"20955653.25",
#    "pe":"-4.8599",
#    "indicatedPe":"-4.8599",
#    "peTtm":"-4.8738",
#    "eps":"-1.1955",
#    "epsTtm":"-1.1921",
#    "pb":"2.187",
#    "totalShares":"19753061",
#    "outstandingShares":"3606825",
#    "fiftyTwoWkHigh":"12.96",
#    "fiftyTwoWkLow":"1.450",
#    "yield":"0.0000",
#    "baSize":0,
#    "ntvSize":30,
#    "depth":{
#       "ntvAggAskList":[
#          {
#             "price":"8.97",
#             "volume":"100"
#          },
#          {
#             "price":"8.99",
#             "volume":"7"
#          },
#          ...
#       ],
#       "ntvAggBidList":[
#          {
#             "price":"8.20",
#             "volume":"35"
#          },
#          {
#             "price":"8.15",
#             "volume":"50"
#          },
#          ...
#       ]
#    },
#    "currencyCode":"USD",
#    "lotSize":"1",
#    "ps":"1.112",
#    "bps":"2.656",
#    "estimateEarningsDate":"",
#    "tradeStatus":"D"
# }


def get_quote(ticker_id=None):
    time.sleep(1)
    try:
        return wb_instance.get_quote(tId=ticker_id)
    except Exception as e:
        print("[{}] get_quote exception: {}".format(utils.get_now(), e))
        return None


#                            open  high   low  close  volume  vwap
# timestamp
# 2021-04-07 19:34:00-04:00  8.36  8.36  8.36   8.36    25.0  8.46
# 2021-04-07 19:35:00-04:00  8.36  8.36  8.36   8.36    12.0  8.46
# 2021-04-07 19:37:00-04:00  8.42  8.42  8.42   8.42    18.0  8.46
# 2021-04-07 19:38:00-04:00  8.36  8.36  8.36   8.36   375.0  8.46
# 2021-04-07 19:40:00-04:00  8.47  8.50  8.47   8.50  2533.0  8.46
# 2021-04-07 19:42:00-04:00  8.47  8.47  8.47   8.47    17.0  8.46
# 2021-04-07 19:50:00-04:00  8.56  8.60  8.56   8.60   300.0  8.46
# 2021-04-07 19:51:00-04:00  8.60  8.60  8.60   8.60   263.0  8.46
# 2021-04-07 19:56:00-04:00  8.60  8.60  8.60   8.60    25.0  8.46
# 2021-04-07 20:00:00-04:00  8.65  8.65  8.65   8.65   100.0  8.46

def get_1m_bars(ticker_id=None, count=10):
    time.sleep(1)
    try:
        return wb_instance.get_bars(tId=ticker_id, interval='m1', count=count, extendTrading=1)
    except Exception as e:
        print("[{}] get_1m_bars exception: {}".format(utils.get_now(), e))
        return pd.DataFrame()

# symbol = 'AVCT'
# ticker_id = 925348770


def buy_limit_order(ticker_id=None, price=0, quant=0):
    return wb_instance.place_order(
        tId=ticker_id,
        price=price,
        action='BUY',
        orderType='LMT',
        quant=quant,
    )


def sell_limit_order(ticker_id=None, price=0, quant=0):
    return wb_instance.place_order(
        tId=ticker_id,
        price=price,
        action='SELL',
        orderType='LMT',
        quant=quant,
    )


def cancel_order(order_id):
    return wb_instance.cancel_order(order_id)

# [
#    {
#       "id":10395509,
#       "accountId":4493986,
#       "paperId":1,
#       "ticker":{
#          "tickerId":925348770,
#          "symbol":"AVCT",
#          "name":"American Virtual Cloud Technologies",
#          "tinyName":"American Virtual Cloud Technologies",
#          "listStatus":1,
#          "exchangeCode":"NAS",
#          "exchangeId":10,
#          "extType":[

#          ],
#          "type":2,
#          "regionId":6,
#          "regionName":"美国",
#          "regionIsoCode":"US",
#          "currencyId":247,
#          "currencyCode":"USD",
#          "disExchangeCode":"NASDAQ",
#          "disSymbol":"AVCT"
#       },
#       "status":1,
#       "position":"1",
#       "cost":"7.55",
#       "costPrice":"7.550",
#       "currency":"USD",
#       "lastPrice":"7.56",
#       "marketValue":"7.56",
#       "unrealizedProfitLoss":"0.01",
#       "unrealizedProfitLossRate":"0.0013",
#       "lotSize":1
#    }
# ]


def get_positions():
    time.sleep(1)
    try:
        return wb_instance.get_positions()
    except Exception as e:
        print("[{}] get_positions exception: {}".format(utils.get_now(), e))
        return None


def get_current_orders():
    time.sleep(1)
    try:
        return wb_instance.get_current_orders()
    except Exception as e:
        print("[{}] get_current_orders exception: {}".format(utils.get_now(), e))
        return None


def get_history_orders():
    time.sleep(1)
    try:
        return wb_instance.get_history_orders()
    except Exception as e:
        print("[{}] get_history_orders exception: {}".format(utils.get_now(), e))
        return None


def _get_browser_headers():
    return {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        "referer": "quotes-gw.webullfintech.com/",
        "Accept-Encoding": None,
    }


# [{'timestamp': 1617840000, 'open': 8.65, 'close': 8.65, 'high': 8.65, 'low': 8.65, 'volume': 100, 'vwap': 8.46}, ...]

def get_1m_charts(ticker_id, count=20):
    time.sleep(1)
    session = requests.Session()
    url = WEBULL_QUOTE_1M_CHARTS_URL.format(ticker_id, count)
    res = session.get(url, headers=_get_browser_headers())
    res_json = json.loads(res.text)
    if len(res_json) == 0:
        return []
    record_list = res_json[0]["data"]
    ret_list = []
    for record in record_list:
        record_parts = record.split(",")
        timestamp = int(record_parts[0])
        open_price = float(record_parts[1])
        close_price = float(record_parts[2])
        high_price = float(record_parts[3])
        low_price = float(record_parts[4])
        volume = int(record_parts[6])
        vwap = float(record_parts[7])
        ret_list.append({
            "timestamp": timestamp,
            "open": open_price,
            "close": close_price,
            "high": high_price,
            "low": low_price,
            "volume": volume,
            "vwap": vwap,
        })
    return ret_list


def get_pre_market_gainers():
    time.sleep(1)
    session = requests.Session()
    res = session.get(
        WEBULL_PRE_MARKET_GAINERS_URL,
        headers=_get_browser_headers())
    res_json = json.loads(res.text)
    obj_list = res_json["data"]
    gainers = []
    for json_obj in obj_list:
        ticker_obj = json_obj["ticker"]
        values_obj = json_obj["values"]
        symbol = ticker_obj["symbol"]
        ticker_id = ticker_obj["tickerId"]
        change = float(values_obj["change"])
        change_percentage = float(values_obj["changeRatio"])
        price = float(values_obj["price"])
        gainers.append(
            {
                "symbol": symbol,
                "ticker_id": ticker_id,
                "change": change,
                "change_percentage": change_percentage,
                "price": price,
            }
        )
    return gainers


def get_top_gainers():
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_TOP_GAINERS_URL,
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            symbol = ticker_obj["symbol"]
            ticker_id = ticker_obj["tickerId"]
            change = float(values_obj["change"])
            change_percentage = float(values_obj["changeRatio"])
            price = float(ticker_obj["pprice"])
            gainers.append(
                {
                    "symbol": symbol,
                    "ticker_id": ticker_id,
                    "change": change,
                    "change_percentage": change_percentage,
                    "price": price,
                }
            )
        return gainers
    except Exception as e:
        print("[{}] get_top_gainers exception: {}".format(utils.get_now(), e))
        return []


def get_after_market_gainers():
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_AFTER_MARKET_GAINERS_URL,
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            symbol = ticker_obj["symbol"]
            ticker_id = ticker_obj["tickerId"]
            change = float(values_obj["change"])
            change_percentage = float(values_obj["changeRatio"])
            price = float(values_obj["price"])
            gainers.append(
                {
                    "symbol": symbol,
                    "ticker_id": ticker_id,
                    "change": change,
                    "change_percentage": change_percentage,
                    "price": price,
                }
            )
        return gainers
    except Exception as e:
        print("[{}] get_after_market_gainers exception: {}".format(
            utils.get_now(), e))
        return []


def get_top_losers():
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_TOP_LOSERS_URL,
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        losers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            symbol = ticker_obj["symbol"]
            ticker_id = ticker_obj["tickerId"]
            change = float(values_obj["change"])
            change_percentage = float(values_obj["changeRatio"])
            price = float(ticker_obj["pprice"])
            losers.append(
                {
                    "symbol": symbol,
                    "ticker_id": ticker_id,
                    "change": change,
                    "change_percentage": change_percentage,
                    "price": price,
                }
            )
        return losers
    except Exception as e:
        print("[{}] get_top_losers exception: {}".format(utils.get_now(), e))
        return []


def get_after_market_losers():
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_AFTER_MARKET_LOSERS_URL,
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            symbol = ticker_obj["symbol"]
            ticker_id = ticker_obj["tickerId"]
            change = float(values_obj["change"])
            change_percentage = float(values_obj["changeRatio"])
            price = float(values_obj["price"])
            gainers.append(
                {
                    "symbol": symbol,
                    "ticker_id": ticker_id,
                    "change": change,
                    "change_percentage": change_percentage,
                    "price": price,
                }
            )
        return gainers
    except Exception as e:
        print("[{}] get_after_market_losers exception: {}".format(
            utils.get_now(), e))
        return []
