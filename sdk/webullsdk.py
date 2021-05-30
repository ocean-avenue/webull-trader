import requests
import json
import time
from webull import webull, paper_webull
import pandas as pd
from scripts import utils
from sdk.config import WEBULL_AFTER_MARKET_LOSERS_URL, WEBULL_PRE_MARKET_GAINERS_URL, WEBULL_AFTER_MARKET_GAINERS_URL, WEBULL_QUOTE_1M_CHARTS_URL, WEBULL_TOP_GAINERS_URL, WEBULL_TOP_LOSERS_URL
from webull_trader.models import WebullCredentials

wb_instance = None


def _get_instance(paper=True):
    global wb_instance
    if wb_instance:
        return wb_instance
    if paper:
        return paper_webull()
    else:
        return webull()


def login(paper=True):
    global wb_instance
    if paper:
        wb_instance = paper_webull()
    else:
        wb_instance = webull()

    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        print("[{}] Can not load webull credentials, login failed!".format(
            utils.get_now()))
        return False

    credentials_data = json.loads(credentials.cred)

    wb_instance._refresh_token = credentials_data['refreshToken']
    wb_instance._access_token = credentials_data['accessToken']
    wb_instance._token_expire = credentials_data['tokenExpireTime']
    wb_instance._uuid = credentials_data['uuid']

    try:
        # refresh login
        n_data = wb_instance.refresh_login()

        credentials_data['refreshToken'] = n_data['refreshToken']
        credentials_data['accessToken'] = n_data['accessToken']
        credentials_data['tokenExpireTime'] = n_data['tokenExpireTime']

        utils.save_webull_credentials(json.dumps(credentials_data), paper)
    except Exception as e:
        print("[{}] ⚠️  Exception refresh_login: {}".format(utils.get_now(), e))
        return False

    wb_instance.get_account_id()
    return True


def logout():
    instance = _get_instance()
    instance.logout()
    return True


# {
#    "accountId":4493986,
#    "currency":"USD",
#    "currencyId":247,
#    "netLiquidation":"5251.69",
#    "totalProfitLoss":"251.69",
#    "totalProfitLossRate":"0.0503",
#    "accountMembers":[
#       {
#          "key":"totalMarketValue",
#          "value":"0.00"
#       },
#       {
#          "key":"usableCash",
#          "value":"5251.69"
#       },
#       {
#          "key":"dayProfitLoss",
#          "value":"309.23"
#       }
#    ],
#    "accounts":[
#       {
#          "id":4493986,
#          "paperId":1,
#          "status":0,
#          "paperType":0,
#          "paperName":"Paper Trading",
#          "paperTickerPoolCode":"wb_week",
#          "currency":"USD",
#          "currencyId":247,
#          "supportOutsideRth":true,
#          "timeInForces":[
#             "DAY",
#             "GTC"
#          ],
#          "orderTypes":[
#             "MKT",
#             "LMT"
#          ]
#       }
#    ],
#    "openOrders":[

#    ],
#    "openOrderSize":0,
#    "positions":[

#    ],
#    "actBaseUrl":"https://act.webull.com/contentEdit/paperRule.html"
# }

def get_account():
    instance = _get_instance()
    return instance.get_account()


# {'totalMarketValue': '0.00', 'usableCash': '4876.63', 'dayProfitLoss': '-133.15'}

def get_portfolio():
    instance = _get_instance()
    return instance.get_portfolio()


def get_trade_token(password=''):
    instance = _get_instance()
    return instance.get_trade_token(password=password)

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
        instance = _get_instance()
        return instance.get_quote(tId=ticker_id)
    except Exception as e:
        print("[{}] ⚠️  Exception get_quote: {}".format(utils.get_now(), e))
        return None


def get_ticker(symbol=None):
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_ticker(stock=symbol)
    except Exception as e:
        print("[{}] ⚠️  Exception get_ticker: {}".format(utils.get_now(), e))
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

def get_1m_bars(ticker_id=None, count=20, timestamp=None):
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_bars(tId=ticker_id, interval='m1', count=count, extendTrading=1, timeStamp=timestamp)
    except Exception as e:
        print("[{}] ⚠️  Exception get_1m_bars: {}".format(utils.get_now(), e))
        return pd.DataFrame()


def get_1d_bars(ticker_id=None, count=20):
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_bars(tId=ticker_id, interval='d1', count=count, extendTrading=1)
    except Exception as e:
        print("[{}] ⚠️  Exception get_1d_bars: {}".format(utils.get_now(), e))
        return pd.DataFrame()

# symbol = 'AVCT'
# ticker_id = 925348770
# symbol = 'AAPL'
# ticker_id = 913256135


def buy_limit_order(ticker_id=None, price=0, quant=0):
    instance = _get_instance()
    return instance.place_order(
        tId=ticker_id,
        price=price,
        action='BUY',
        orderType='LMT',
        quant=quant,
    )


def buy_market_order(ticker_id=None, quant=0):
    instance = _get_instance()
    return instance.place_order(
        tId=ticker_id,
        action='BUY',
        orderType='MKT',
        quant=quant,
    )


def sell_limit_order(ticker_id=None, price=0, quant=0):
    instance = _get_instance()
    return instance.place_order(
        tId=ticker_id,
        price=price,
        action='SELL',
        orderType='LMT',
        quant=quant,
    )


def sell_market_order(ticker_id=None, quant=0):
    instance = _get_instance()
    return instance.place_order(
        tId=ticker_id,
        action='SELL',
        orderType='MKT',
        quant=quant,
    )


def cancel_order(order_id):
    instance = _get_instance()
    return instance.cancel_order(order_id)


def cancel_all_orders():
    instance = _get_instance()
    instance.cancel_all_orders()


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
        instance = _get_instance()
        return instance.get_positions()
    except Exception as e:
        print("[{}] ⚠️  Exception get_positions: {}".format(utils.get_now(), e))
        return None


def get_current_orders():
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_current_orders()
    except Exception as e:
        print("[{}] ⚠️  Exception get_current_orders: {}".format(
            utils.get_now(), e))
        return None

# Paper
# [
#    {
#       "orderId":40281415,
#       "paperId":1,
#       "action":"SELL",
#       "totalQuantity":"374",
#       "filledQuantity":"374",
#       "filledTime":"05/07/2021 16:41:30 EDT",
#       "filledTime0":1620420090874,
#       "placedTime":"05/07/2021 16:41:26 EDT",
#       "timeInForce":"GTC",
#       "orderType":"LMT",
#       "lmtPrice":"2.600",
#       "avgFilledPrice":"2.650",
#       "ticker":{
#          "tickerId":925238443,
#          "symbol":"PTIX",
#          "name":"Protagenic",
#          "tinyName":"Protagenic",
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
#          "secType":[
#             61
#          ],
#          "disExchangeCode":"NASDAQ",
#          "disSymbol":"PTIX"
#       },
#       "canModify":false,
#       "canCancel":false,
#       "createTime":"05/07/2021 16:41:25 EDT",
#       "createTime0":1620420085040,
#       "status":"Filled",
#       "statusStr":"Filled",
#       "outsideRegularTradingHour":true,
#       "filledValue":"991.10"
#    },
#    ...
# ]

# Live
# [
#    {
#       "comboTickerType":"stock",
#       "outsideRegularTradingHour":true,
#       "orders":[
#          {
#             "orderId":444119537793646592,
#             "tickerType":"EQUITY",
#             "ticker":{
#                "tickerId":950167487,
#                "symbol":"MP",
#                "name":"MP Materials Corporation",
#                "tinyName":"MP Materials Corporation",
#                "listStatus":1,
#                "exchangeCode":"NYSE",
#                "exchangeId":11,
#                "type":2,
#                "regionId":6,
#                "currencyId":247,
#                "currencyCode":"USD",
#                "secType":[
#                   61
#                ],
#                "disExchangeCode":"NYSE",
#                "disSymbol":"MP"
#             },
#             "action":"BUY",
#             "orderType":"LMT",
#             "lmtPrice":"32.00",
#             "totalQuantity":"5",
#             "tickerId":950167487,
#             "timeInForce":"DAY",
#             "optionExercisePrice":"0.00",
#             "filledQuantity":"5",
#             "entrustType":"QTY",
#             "placeAmount":"0",
#             "filledAmount":"0",
#             "remainAmount":"0",
#             "statusCode":"Filled",
#             "statusStr":"Filled",
#             "symbol":"MP",
#             "optionContractMultiplier":"0",
#             "createTime0":1620332279000,
#             "createTime":"05/06/2021 16:17:59 EDT",
#             "filledTime0":1620332280000,
#             "filledTime":"05/06/2021 16:18:00 EDT",
#             "filledValue":"155.00",
#             "avgFilledPrice":"31.00",
#             "canModify":false,
#             "canCancel":false,
#             "assetType":"stock",
#             "brokerId":8,
#             "remainQuantity":"0",
#             "updateTime":"05/06/2021 16:18:10 EDT",
#             "updateTime0":1620332290000,
#             "relation":"normal",
#             "tickerPriceDefineList":[
#                {
#                   "tickerId":950167487,
#                   "rangeBegin":"0",
#                   "containBegin":true,
#                   "rangeEnd":"1",
#                   "containEnd":false,
#                   "priceUnit":"0.0001"
#                },
#                {
#                   "tickerId":950167487,
#                   "rangeBegin":"1",
#                   "containBegin":true,
#                   "containEnd":true,
#                   "priceUnit":"0.01"
#                }
#             ]
#          }
#       ],
#       "quantity":"5",
#       "filledQuantity":"5",
#       "action":"BUY",
#       "status":"Filled",
#       "statusStr":"Filled",
#       "timeInForce":"DAY",
#       "orderType":"LMT",
#       "lmtPrice":"32.00",
#       "canModify":false,
#       "canCancel":false
#    },
#    {
#       "comboTickerType":"stock",
#       "outsideRegularTradingHour":false,
#       "orders":[
#          {
#             "orderId":444112767587201024,
#             "tickerType":"EQUITY",
#             "ticker":{
#                "tickerId":913254324,
#                "symbol":"DQ",
#                "name":"Daqo New Energy",
#                "tinyName":"Daqo New Energy",
#                "listStatus":1,
#                "exchangeCode":"NYSE",
#                "exchangeId":11,
#                "type":2,
#                "regionId":6,
#                "currencyId":247,
#                "currencyCode":"USD",
#                "secType":[
#                   62
#                ],
#                "disExchangeCode":"NYSE",
#                "disSymbol":"DQ"
#             },
#             "action":"BUY",
#             "orderType":"MKT",
#             "totalQuantity":"8",
#             "tickerId":913254324,
#             "timeInForce":"DAY",
#             "optionExercisePrice":"0.00",
#             "filledQuantity":"8",
#             "entrustType":"QTY",
#             "placeAmount":"0",
#             "filledAmount":"0",
#             "remainAmount":"0",
#             "statusCode":"Filled",
#             "statusStr":"Filled",
#             "symbol":"DQ",
#             "optionContractMultiplier":"0",
#             "createTime0":1620330665000,
#             "createTime":"05/06/2021 15:51:05 EDT",
#             "filledTime0":1620330665000,
#             "filledTime":"05/06/2021 15:51:05 EDT",
#             "filledValue":"589.44",
#             "avgFilledPrice":"73.68",
#             "canModify":false,
#             "canCancel":false,
#             "assetType":"stock",
#             "brokerId":8,
#             "remainQuantity":"0",
#             "updateTime":"05/06/2021 15:52:11 EDT",
#             "updateTime0":1620330731000,
#             "relation":"normal",
#             "tickerPriceDefineList":[
#                {
#                   "tickerId":913254324,
#                   "rangeBegin":"0",
#                   "containBegin":true,
#                   "rangeEnd":"1",
#                   "containEnd":false,
#                   "priceUnit":"0.0001"
#                },
#                {
#                   "tickerId":913254324,
#                   "rangeBegin":"1",
#                   "containBegin":true,
#                   "containEnd":true,
#                   "priceUnit":"0.01"
#                }
#             ]
#          }
#       ],
#       "quantity":"8",
#       "filledQuantity":"8",
#       "action":"BUY",
#       "status":"Filled",
#       "statusStr":"Filled",
#       "timeInForce":"DAY",
#       "orderType":"MKT",
#       "canModify":false,
#       "canCancel":false
#    },
#    ...
# ]


def get_history_orders(status='All', count=1000):
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_history_orders(status=status, count=count)
    except Exception as e:
        print("[{}] ⚠️  Exception get_history_orders: {}".format(
            utils.get_now(), e))
        return None

# [
#    {
#       "id":41413595,
#       "title":"US Indexes End Lower on Last Day of April",
#       "sourceName":"GuruFocus News",
#       "newsTime":"2021-05-01T21:19:00.556+0000",
#       "summary":"",
#       "newsUrl":"https://www.gurufocus.com/news/1412728/us-indexes-end-lower-on-last-day-of-april/?r=21637c73084e87d770a98f867757282f",
#       "siteType":1,
#       "collectSource":"cnn"
#    },
#    ...
# ]


def get_news(stock=None, items=5):
    '''
    get news and returns a list of articles
    params:
        Id: 0 is latest news article
        items: number of articles to return
    '''
    time.sleep(1)
    try:
        instance = _get_instance()
        return instance.get_news(stock=stock, Id=0, items=items)
    except Exception as e:
        print("[{}] ⚠️  Exception get_news: {}".format(
            utils.get_now(), e))
        return []


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


def get_pre_market_gainers(count=10):
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_PRE_MARKET_GAINERS_URL.format(count),
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            if ticker_obj["template"] == "stock":
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
        print("[{}] ⚠️  Exception get_pre_market_gainers: {}".format(
            utils.get_now(), e))
        return []


# [
#    {
#       "symbol":"MOSY",
#       "ticker_id":913323981,
#       "change":1.67,
#       "change_percentage":0.4406,
#       "price":5.15
#    },
#   ...
# ]


def get_top_gainers(count=10):
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_TOP_GAINERS_URL.format(count),
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            if ticker_obj["template"] == "stock":
                symbol = ticker_obj["symbol"]
                ticker_id = ticker_obj["tickerId"]
                change = float(values_obj["change"])
                change_percentage = float(values_obj["changeRatio"])
                price = float(ticker_obj["pprice"])
                close = float(ticker_obj["close"])
                gainers.append(
                    {
                        "symbol": symbol,
                        "ticker_id": ticker_id,
                        "change": change,
                        "change_percentage": change_percentage,
                        "price": price,
                        "close": close,
                    }
                )
        return gainers
    except Exception as e:
        print("[{}] ⚠️  Exception get_top_gainers: {}".format(utils.get_now(), e))
        return []


def get_after_market_gainers(count=10):
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_AFTER_MARKET_GAINERS_URL.format(count),
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            if ticker_obj["template"] == "stock":
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
        print("[{}] ⚠️  Exception get_after_market_gainers: {}".format(
            utils.get_now(), e))
        return []


# [
#    {
#       "symbol":"JZXN",
#       "ticker_id":950172499,
#       "change":-8.67,
#       "change_percentage":-0.4656,
#       "price":9.61
#    },
#   ...
# ]


def get_top_losers(count=10):
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_TOP_LOSERS_URL.format(count),
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        losers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            if ticker_obj["template"] == "stock":
                symbol = ticker_obj["symbol"]
                ticker_id = ticker_obj["tickerId"]
                change = float(values_obj["change"])
                change_percentage = float(values_obj["changeRatio"])
                price = float(ticker_obj["pprice"])
                close = float(ticker_obj["close"])
                losers.append(
                    {
                        "symbol": symbol,
                        "ticker_id": ticker_id,
                        "change": change,
                        "change_percentage": change_percentage,
                        "price": price,
                        "close": close,
                    }
                )
        return losers
    except Exception as e:
        print("[{}] ⚠️  Exception get_top_losers: {}".format(utils.get_now(), e))
        return []


def get_after_market_losers(count=10):
    time.sleep(1)
    try:
        session = requests.Session()
        res = session.get(
            WEBULL_AFTER_MARKET_LOSERS_URL.format(count),
            headers=_get_browser_headers())
        res_json = json.loads(res.text)
        obj_list = res_json["data"]
        gainers = []
        for json_obj in obj_list:
            ticker_obj = json_obj["ticker"]
            values_obj = json_obj["values"]
            if ticker_obj["template"] == "stock":
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
        print("[{}] ⚠️  Exception get_after_market_losers: {}".format(
            utils.get_now(), e))
        return []
