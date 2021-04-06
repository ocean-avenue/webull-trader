import requests
import json
import time
from webull import webull, paper_webull
from sdk.config import WEBULL_AFTER_MARKET_LOSERS_URL, WEBULL_PRE_MARKET_GAINERS_URL, WEBULL_AFTER_MARKET_GAINERS_URL, WEBULL_QUOTE_1M_CHARTS_URL, WEBULL_TOP_GAINERS_URL, WEBULL_TOP_LOSERS_URL

wb_instance = None


def init_webull(paper=True):
    global wb_instance
    if paper:
        wb_instance = paper_webull()
    else:
        wb_instance = webull()


def login():
    input = open('sdk/webull_credentials.json', 'r')
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

    output = open('sdk/webull_credentials.json', 'w')
    json.dump(credential_data, output)
    output.close()

    wb_instance.get_account_id()


def place_order(ticker_id=None, price=0, action='BUY', order_type='LMT', enforce='GTC', quant=0, extend_hour=True, stop_price=None, trial_value=0, trial_type='DOLLAR'):
    wb_instance.place_order(
        tId=ticker_id,
        price=price,
        action=action,
        orderType=order_type,
        enforce=enforce,
        quant=quant,
        outsideRegularTradingHour=extend_hour,
        stpPrice=stop_price,
        trial_value=trial_value,
        trial_type=trial_type,
    )


def _get_browser_headers():
    return {
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 11_2_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.90 Safari/537.36",
        "referer": "quotes-gw.webullfintech.com/",
        "Accept-Encoding": None,
    }


def get_quote_1m_charts(ticker_id):
    time.sleep(1)
    session = requests.Session()
    url = WEBULL_QUOTE_1M_CHARTS_URL.format(ticker_id)
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


def get_after_market_gainers():
    time.sleep(1)
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


def get_top_losers():
    time.sleep(1)
    session = requests.Session()
    res = session.get(
        WEBULL_TOP_LOSERS_URL,
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


def get_after_market_losers():
    time.sleep(1)
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
