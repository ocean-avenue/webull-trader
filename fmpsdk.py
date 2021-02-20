import json
from urllib.request import urlopen
from config import FMP_API_KEY

API_BASE_URL = "https://financialmodelingprep.com/api/v3"

def _get_jsonparsed_data(url):
    """
    Receive the content of ``url``, parse it as JSON and return the object.

    Parameters
    ----------
    url : str

    Returns
    -------
    dict
    """
    response = urlopen(url)
    data = response.read().decode("utf-8")
    return json.loads(data)


def get_most_gainers():
    return _get_jsonparsed_data(
        "{}/gainers?apikey={}".format(API_BASE_URL, FMP_API_KEY)
    )


def get_quotes(symbol_list):
    return _get_jsonparsed_data(
        "{}/quote/{}?apikey={}".format(API_BASE_URL, ",".join(symbol_list), FMP_API_KEY)
    )


def get_quote_short(symbol):
    return _get_jsonparsed_data(
        "{}/quote-short/{}?apikey={}".format(API_BASE_URL, symbol, FMP_API_KEY)
    )[0]


def get_intraday_sma(symbol, interval, period):
    return _get_jsonparsed_data(
        "{}/technical_indicator/{}/{}?period={}&type=sma&apikey={}".format(
            API_BASE_URL, interval, symbol, period, FMP_API_KEY
        )
    )