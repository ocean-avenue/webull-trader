import json
import time
import requests
import traceback
import pandas as pd
from typing import List, Optional
from common import utils, db
from logger import trading_logger
from webull import webull, paper_webull
from webull_trader.models import WebullCredentials


# https://app.webull.com/market/region/6
WEBULL_DAILY_PL_URL = "https://ustrade.webullbroker.com/api/trading/v1/profitloss/account/period?dateRangeType=all&periodType=Day&secAccountId={}"
WEBULL_TICKER_QUOTE_URL = "https://quotes-gw.webullbroker.com/api/quotes/ticker/getTickerRealTime?tickerId={}&includeSecu=1&includeQuote=1"
WEBULL_TOP_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=1d&pageIndex=1&pageSize={}"
WEBULL_PRE_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=preMarket&pageIndex=1&pageSize={}"
WEBULL_AFTER_MARKET_GAINERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/topGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize={}"
WEBULL_TOP_LOSERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/dropGainers?regionId=6&rankType=1d&pageIndex=1&pageSize={}"
WEBULL_AFTER_MARKET_LOSERS_URL = "https://quotes-gw.webullbroker.com/api/wlas/ranking/dropGainers?regionId=6&rankType=afterMarket&pageIndex=1&pageSize={}"
WEBULL_PRE_MARKET_LOSERS_URL = "https://quotes-gw.webullfintech.com/api/wlas/ranking/dropGainers?regionId=6&rankType=preMarket&pageIndex=1&pageSize={}"
WEBULL_QUOTE_1M_CHARTS_URL = "https://quotes-gw.webullbroker.com/api/quote/charts/query?tickerIds={}&type=m1&count={}&extendTrading=1"


ORDER_STATUS_CANCELED = "Cancelled"
ORDER_STATUS_FILLED = "Filled"
ORDER_STATUS_WORKING = "Working"
ORDER_STATUS_PARTIALLY_FILLED = "Partially Filled"
ORDER_STATUS_PENDING = "Pending"
ORDER_STATUS_PENDING = "Pending Cancel"
ORDER_STATUS_FAILED = "Failed"
ORDER_STATUS_ALL = "All"

ORDER_STATUS_NOT_FOUND = "Not Found"

API_DELAY_IN_SEC = 1.0


def _get_browser_headers() -> dict:
    return {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        "referer": "quotes-gw.webullfintech.com/",
        "Accept-Encoding": None,
    }


_wb_instance: webull = None
_wb_paper: bool = True
_wb_trade_pwd: str = "123456"


def _get_instance() -> webull:
    global _wb_instance
    global _wb_paper
    if _wb_instance:
        return _wb_instance
    if _wb_paper:
        return paper_webull()
    else:
        return webull()


def login(paper: bool = True) -> bool:
    global _wb_instance
    global _wb_paper
    global _wb_trade_pwd
    if paper:
        _wb_instance = paper_webull()
    else:
        _wb_instance = webull()
    _wb_paper = paper

    credentials = WebullCredentials.objects.filter(paper=paper).first()
    if not credentials:
        trading_logger.log(
            "Can not load webull credentials, login failed!")
        return False

    credentials_data = json.loads(credentials.cred)
    _wb_trade_pwd = credentials.trade_pwd

    _wb_instance._refresh_token = credentials_data['refreshToken']
    _wb_instance._access_token = credentials_data['accessToken']
    _wb_instance._token_expire = credentials_data['tokenExpireTime']
    _wb_instance._uuid = credentials_data['uuid']

    try:
        # refresh login
        n_data = _wb_instance.refresh_login()

        credentials_data['refreshToken'] = n_data['refreshToken']
        credentials_data['accessToken'] = n_data['accessToken']
        credentials_data['tokenExpireTime'] = n_data['tokenExpireTime']

        db.save_webull_credentials(json.dumps(credentials_data), paper)
    except Exception as e:
        trading_logger.log("⚠️  Exception refresh_login: {}".format(e))
        return False

    _wb_instance.get_account_id()
    return True


def logout() -> bool:
    instance = _get_instance()
    instance.logout()
    return True


# Paper
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
#
# Live
# {
#    "banners":[
#       ...
#    ],
#    "secAccountId":13169104,
#    "brokerId":8,
#    "accountType":"MRGN",
#    "brokerAccountId":"5NK43899",
#    "currency":"USD",
#    "currencyId":247,
#    "pdt":false,
#    "professional":false,
#    "showUpgrade":false,
#    "totalCost":"0.00",
#    "netLiquidation":"1413.80",
#    "unrealizedProfitLoss":"0.00",
#    "unrealizedProfitLossRate":"0.0000",
#    "unrealizedProfitLossBase":"1413.80",
#    "warning":false,
#    "remindModifyPwd":false,
#    "accountMembers":[
#       {
#          "key":"totalMarketValue",
#          "value":"0.00"
#       },
#       {
#          "key":"cashBalance",
#          "value":"1413.80"
#       },
#       {
#          "key":"dayBuyingPower",
#          "value":"1413.80"
#       },
#       {
#          "key":"overnightBuyingPower",
#          "value":"1413.80"
#       },
#       {
#          "key":"cryptoBuyingPower",
#          "value":"626.56"
#       },
#       {
#          "key":"optionBuyingPower",
#          "value":"1413.80"
#       },
#       {
#          "key":"riskStatus",
#          "value":"Safe",
#          "data":{
#             "warning":false,
#             "level":"SAFE",
#             "levelStr":"Safe",
#             "riskWarning":false,
#             "gfvCount":0,
#             "marginWarning":false,
#             "smaWarning":false,
#             "url":"https://act.webull.com/v-trade/v-main.html?secAccountId=13169104#/risk-status"
#          }
#       },
#       {
#          "key":"remainTradeTimes",
#          "value":"3,3,3,3,3",
#          "data":{
#             "url":"https://act.webull.com/v-trade/v-main.html?secAccountId=13169104#/day-transaction"
#          }
#       }
#    ],
#    "positions":[],
#    "openOrders":[],
#    "positions2":[],
#    "openOrders2":[],
#    "openIpoOrders":[],
#    "openOrderSize":0
# }

def get_account() -> dict:
    instance = _get_instance()
    return instance.get_account()


def get_account_id() -> Optional[str]:
    instance = _get_instance()
    return instance._account_id

# Paper
# {'totalMarketValue': '0.00', 'usableCash': '4876.63', 'dayProfitLoss': '-133.15'}
#
# Live
# {
#    "totalMarketValue":"0.00",
#    "cashBalance":"1413.80",
#    "dayBuyingPower":"1413.80",
#    "overnightBuyingPower":"1413.80",
#    "cryptoBuyingPower":"626.56",
#    "optionBuyingPower":"1413.80",
#    "riskStatus":"Safe",
#    "remainTradeTimes":"3,3,3,3,3",
# }


def get_portfolio() -> dict:
    instance = _get_instance()
    data = instance.get_account()
    output = {}
    if 'accountMembers' in data:
        for item in data['accountMembers']:
            output[item['key']] = item['value']
    if 'totalMarketValue' not in output:
        output['totalMarketValue'] = '0.00'
    if 'usableCash' not in output:
        output['usableCash'] = '0.00'
    if 'dayProfitLoss' not in output:
        output['dayProfitLoss'] = '0.00'
    if 'cashBalance' not in output:
        output['cashBalance'] = '0.00'
    if 'dayBuyingPower' not in output:
        output['dayBuyingPower'] = '0.00'
    if 'overnightBuyingPower' not in output:
        output['overnightBuyingPower'] = '0.00'
    if 'cryptoBuyingPower' not in output:
        output['cryptoBuyingPower'] = '0.00'
    if 'optionBuyingPower' not in output:
        output['optionBuyingPower'] = '0.00'
    if 'riskStatus' not in output:
        output['riskStatus'] = 'Safe'
    if 'remainTradeTimes' not in output:
        output['remainTradeTimes'] = 'Safe'
    return output


def get_usable_cash() -> float:
    try:
        global _wb_paper
        portfolio = get_portfolio()
        usable_cash = 0.0
        if _wb_paper:
            usable_cash = float(portfolio['usableCash'])
        else:
            usable_cash = float(portfolio['cashBalance'])
        return usable_cash
    except Exception as e:
        trading_logger.log("⚠️  Exception get_usable_cash: {}".format(e))
        return 0.0


def get_day_profit_loss() -> str:
    try:
        global _wb_paper
        day_profit_loss = "-"
        if _wb_paper:
            portfolio = get_portfolio()
            if "dayProfitLoss" in portfolio:
                day_profit_loss = portfolio['dayProfitLoss']
        else:
            daily_pl = get_daily_profitloss()
            if len(daily_pl) > 0:
                day_profit_loss = daily_pl[-1]['profitLoss']
        return day_profit_loss
    except Exception as e:
        trading_logger.log("⚠️  Exception get_day_profit_loss: {}".format(e))
        return '-'


def get_trade_token(password='') -> bool:
    instance = _get_instance()
    return instance.get_trade_token(password=password)


# [
#    ...
#    {
#       "periodName":"2021-06-19",
#       "profitLoss":"0.00",
#       "yieldRate":"0.0000",
#       "tradingDay":false
#    },
#    {
#       "periodName":"2021-06-20",
#       "profitLoss":"0.00",
#       "yieldRate":"0.0000",
#       "tradingDay":false
#    },
#    {
#       "periodName":"2021-06-21",
#       "profitLoss":"0.00",
#       "yieldRate":"0.0000",
#       "tradingDay":true
#    }
# ]

def get_daily_profitloss() -> List[dict]:
    instance = _get_instance()
    headers = instance.build_req_headers()
    response = requests.get(WEBULL_DAILY_PL_URL.format(
        get_account_id()), headers=headers)
    result = response.json()
    return result

# Level 2
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
# Level 1
# {
#    "tickerId":913256135,
#    "exchangeId":96,
#    "type":2,
#    "secType":[
#       61
#    ],
#    "regionId":6,
#    "regionCode":"US",
#    "currencyId":247,
#    "name":"Apple",
#    "symbol":"AAPL",
#    "disSymbol":"AAPL",
#    "disExchangeCode":"NASDAQ",
#    "exchangeCode":"NSQ",
#    "listStatus":1,
#    "template":"stock",
#    "derivativeSupport":1,
#    "tradeTime":"2021-08-26T19:25:08.618+0000",
#    "status":"T",
#    "close":"147.80",
#    "change":"-0.56",
#    "changeRatio":"-0.0038",
#    "marketValue":"2527754820800.00",
#    "volume":"39258748",
#    "turnoverRate":"0.0023",
#    "timeZone":"America/New_York",
#    "tzName":"EDT",
#    "preClose":"148.36",
#    "open":"148.35",
#    "high":"149.12",
#    "low":"147.51",
#    "vibrateRatio":"0.0109",
#    "avgVol10D":"73969303",
#    "avgVol3M":"76582930",
#    "negMarketValue":"2526102450941.80",
#    "pe":"45.12",
#    "forwardPe":"26.47",
#    "indicatedPe":"28.52",
#    "peTtm":"28.95",
#    "eps":"3.275",
#    "epsTtm":"5.11",
#    "pb":"38.07",
#    "totalShares":"17102536000",
#    "outstandingShares":"17091356231",
#    "fiftyTwoWkHigh":"151.68",
#    "fiftyTwoWkLow":"103.10",
#    "dividend":"0.8800",
#    "yield":"0.0060",
#    "baSize":1,
#    "ntvSize":0,
#    "askList":[
#       {
#          "price":"147.81",
#          "volume":"742"
#       }
#    ],
#    "bidList":[
#       {
#          "price":"147.79",
#          "volume":"1142"
#       }
#    ],
#    "currencyCode":"USD",
#    "lotSize":"1",
#    "latestDividendDate":"2021-08-06",
#    "latestSplitDate":"2020-08-31",
#    "latestEarningsDate":"2021-07-27",
#    "ps":"7.25",
#    "bps":"3.882",
#    "estimateEarningsDate":"10/27-11/01",
#    "tradeStatus":"T",
#    "bboValve":0
# }


def get_quote(ticker_id=None) -> Optional[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_quote(tId=ticker_id)
    except Exception as e:
        trading_logger.log("⚠️  Exception get_quote: {}".format(e))
        return None


def get_ask_price_from_quote(quote: dict) -> Optional[float]:
    if quote:
        if 'askList' in quote and len(quote['askList']) > 0:
            return float(quote['askList'][0]['price'])
        if 'depth' in quote and 'ntvAggAskList' in quote['depth'] and len(quote['depth']['ntvAggAskList']) > 0:
            return float(quote['depth']['ntvAggAskList'][0]['price'])
    return None


def get_bid_price_from_quote(quote: dict) -> Optional[float]:
    if quote:
        if 'bidList' in quote and len(quote['bidList']) > 0:
            return float(quote['bidList'][0]['price'])
        if 'depth' in quote and 'ntvAggBidList' in quote['depth'] and len(quote['depth']['ntvAggBidList']) > 0:
            return float(quote['depth']['ntvAggBidList'][0]['price'])
    return None


def get_bid_volume_from_quote(quote: dict) -> float:
    if quote:
        if 'bidList' in quote and len(quote['bidList']) > 0:
            return int(quote['bidList'][0]['volume'])
        if 'depth' in quote and 'ntvAggBidList' in quote['depth'] and len(quote['depth']['ntvAggBidList']) > 0:
            return float(quote['depth']['ntvAggBidList'][0]['volume'])
    return 0


def get_ticker(symbol: Optional[str] = None) -> Optional[str]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_ticker(stock=symbol)
    except Exception as e:
        trading_logger.log("⚠️  Exception get_ticker: {}".format(e))
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

def get_1m_bars(ticker_id=None, count=20, timestamp=None) -> pd.DataFrame:
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_bars(tId=ticker_id, interval='m1', count=count, extendTrading=1, timeStamp=timestamp)
    except Exception as e:
        trading_logger.log("⚠️  Exception get_1m_bars: {}".format(e))
        print(traceback.format_exc())
        return pd.DataFrame()


def get_1d_bars(ticker_id=None, count=20) -> pd.DataFrame:
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_bars(tId=ticker_id, interval='d1', count=count, extendTrading=1)
    except Exception as e:
        trading_logger.log("⚠️  Exception get_1d_bars: {}".format(e))
        print(traceback.format_exc())
        return pd.DataFrame()

# symbol = 'AVCT'
# ticker_id = 925348770
# symbol = 'AAPL'
# ticker_id = 913256135


def get_sample_ticker() -> str:
    return '913256135'

# Paper
# {'orderId': 41947352}
# Live
# {'success': True, 'data': {'orderId': 466848369441001472}}


def buy_limit_order(ticker_id=None, price=0, quant=0) -> dict:
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.place_order(
            tId=ticker_id,
            price=price,
            action='BUY',
            orderType='LMT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log("⚠️  Exception buy_limit_order: {}".format(e))
        return {'msg': "Exception during submit buy limit order!"}


def modify_buy_limit_order(ticker_id: str, order_id: str, price=0, quant=0):
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.modify_order(
            {
                'orderId': order_id,
                'ticker': {
                    'tickerId': ticker_id,
                },
                'totalQuantity': quant,
                'outsideRegularTradingHour': True,
            },
            price=price,
            action='BUY',
            orderType='LMT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception modify_buy_limit_order: {}".format(e))
        return {'msg': "Exception during modify buy limit order!"}


# Paper
# {'orderId': 41995367}
# Live
# {'success': True, 'data': {'orderId': 466848369441001472}}


def buy_market_order(ticker_id=None, quant=0) -> dict:
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.place_order(
            tId=ticker_id,
            action='BUY',
            orderType='MKT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log("⚠️  Exception buy_market_order: {}".format(e))
        return {'msg': "Exception during submit buy market order!"}

# Paper
# {'orderId': 41947378}
# Live
# {'success': True, 'data': {'orderId': 466847988010979328}}


def sell_limit_order(ticker_id=None, price=0, quant=0) -> dict:
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.place_order(
            tId=ticker_id,
            price=price,
            action='SELL',
            orderType='LMT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log("⚠️  Exception sell_limit_order: {}".format(e))
        return {'msg': "Exception during submit sell limit order!"}


def modify_sell_limit_order(ticker_id: str, order_id: str, price=0, quant=0):
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.modify_order(
            {
                'orderId': order_id,
                'ticker': {
                    'tickerId': ticker_id,
                },
                'totalQuantity': quant,
                'outsideRegularTradingHour': True,
            },
            price=price,
            action='SELL',
            orderType='LMT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception modify_sell_limit_order: {}".format(e))
        return {'msg': "Exception during modify sell limit order!"}


# Paper
# {'orderId': 41995648}
# Live
# {'success': True, 'data': {'orderId': 466847988010979328}}

def sell_market_order(ticker_id=None, quant=0) -> dict:
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return {'msg': "Get trading token failed!"}
    instance = _get_instance()
    try:
        return instance.place_order(
            tId=ticker_id,
            action='SELL',
            orderType='MKT',
            quant=quant,
            enforce="DAY",
        )
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception sell_market_order: {}".format(e))
        return {'msg': "Exception during submit sell market order!"}


# True
def cancel_order(order_id: str) -> bool:
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return False
    instance = _get_instance()
    try:
        return instance.cancel_order(order_id)
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception cancel_order {}: {}".format(order_id, e))
        return False


def cancel_all_orders():
    global _wb_paper
    global _wb_trade_pwd
    if not _wb_paper and not get_trade_token(_wb_trade_pwd):
        return
    instance = _get_instance()
    instance.cancel_all_orders()


# Paper
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

# Live
# [
#    {
#       "id":502361989079638016,
#       "brokerPosId":"2GHG3ALA6CO10U8B031G1V9JT9",
#       "brokerId":8,
#       "tickerId":950136998,
#       "ticker":{
#          "tickerId":950136998,
#          "symbol":"DDOG",
#          "name":"Datadog Inc",
#          "tinyName":"Datadog Inc",
#          "listStatus":1,
#          "exchangeCode":"NSQ",
#          "exchangeId":96,
#          "type":2,
#          "regionId":6,
#          "currencyId":247,
#          "currencyCode":"USD",
#          "secType":[
#             61
#          ],
#          "disExchangeCode":"NASDAQ",
#          "disSymbol":"DDOG"
#       },
#       "exchange":"NSQ",
#       "position":"1",
#       "assetType":"stock",
#       "cost":"157.08",
#       "costPrice":"157.080",
#       "currency":"USD",
#       "lastPrice":"157.42",
#       "marketValue":"157.42",
#       "unrealizedProfitLoss":"0.34",
#       "unrealizedProfitLossRate":"0.0022",
#       "positionProportion":"0.1430",
#       "exchangeRate":"1",
#       "lastOpenTime":"10/14/2021 13:32:41 GMT",
#       "updatePositionTimeStamp":1634218361892,
#       "lock":false
#    },
#    ...
# ]
def get_positions() -> List[dict]:
    try:
        instance = _get_instance()
        return instance.get_positions()
    except Exception as e:
        trading_logger.log("⚠️  Exception get_positions: {}".format(e))
        return None


def get_current_orders():
    try:
        instance = _get_instance()
        return instance.get_current_orders()
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_current_orders: {}".format(e))
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
#    ...
# ]


def get_history_orders(status=ORDER_STATUS_ALL, count=20) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_history_orders(status=status, count=count)
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_history_orders: {}".format(e))
        return []

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


def get_news(stock=None, items=5) -> List[dict]:
    '''
    get news and returns a list of articles
    params:
        Id: 0 is latest news article
        items: number of articles to return
    '''
    time.sleep(API_DELAY_IN_SEC)
    try:
        instance = _get_instance()
        return instance.get_news(stock=stock, Id=0, items=items)
    except Exception as e:
        trading_logger.log("⚠️  Exception get_news: {}".format(e))
        return []


# [{'timestamp': 1617840000, 'open': 8.65, 'close': 8.65, 'high': 8.65, 'low': 8.65, 'volume': 100, 'vwap': 8.46}, ...]

def get_1m_charts(ticker_id, count=20):
    time.sleep(API_DELAY_IN_SEC)
    session = requests.Session()
    res = session.get(WEBULL_QUOTE_1M_CHARTS_URL.format(
        ticker_id, count), headers=_get_browser_headers())
    res_json = res.json()
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


def get_pre_market_gainers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_PRE_MARKET_GAINERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        gainers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    gainers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return gainers
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_pre_market_gainers: {}".format(e))
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


def get_top_gainers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_TOP_GAINERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        gainers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    gainers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return gainers
    except Exception as e:
        trading_logger.log("⚠️  Exception get_top_gainers: {}".format(e))
        return []


def get_after_market_gainers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_AFTER_MARKET_GAINERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        gainers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    gainers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return gainers
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_after_market_gainers: {}".format(e))
        return []


def get_pre_market_losers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_PRE_MARKET_LOSERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        losers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    losers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return losers
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_pre_market_losers: {}".format(e))
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


def get_top_losers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_TOP_LOSERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        losers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    losers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return losers
    except Exception as e:
        trading_logger.log("⚠️  Exception get_top_losers: {}".format(e))
        return []


def get_after_market_losers(count=10) -> List[dict]:
    time.sleep(API_DELAY_IN_SEC)
    try:
        session = requests.Session()
        res = session.get(WEBULL_AFTER_MARKET_LOSERS_URL.format(
            count), headers=_get_browser_headers())
        res_json = res.json()
        gainers = []
        if "data" in res_json:
            obj_list = res_json["data"]
            for json_obj in obj_list:
                ticker_obj = json_obj["ticker"]
                values_obj = json_obj["values"]
                if ticker_obj["template"] == "stock":
                    symbol = ticker_obj["symbol"]
                    ticker_id = ticker_obj["tickerId"]
                    pprice = utils.get_attr_to_float(ticker_obj, "pprice")
                    close = utils.get_attr_to_float(ticker_obj, "close")
                    market_value = utils.get_attr_to_float(
                        ticker_obj, "marketValue")
                    change = utils.get_attr_to_float(values_obj, "change")
                    change_percentage = utils.get_attr_to_float(
                        values_obj, "changeRatio")
                    gainers.append(
                        {
                            "symbol": symbol,
                            "ticker_id": ticker_id,
                            "change": change,
                            "change_percentage": change_percentage,
                            "pprice": pprice,
                            "close": close,
                            "market_value": market_value,
                        }
                    )
        return gainers
    except Exception as e:
        trading_logger.log(
            "⚠️  Exception get_after_market_losers: {}".format(e))
        return []
