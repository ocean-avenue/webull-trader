import json
from urllib.request import urlopen
from sdk.config import FMP_API_BASE_URL
from credentials.fmp import FMP_API_KEY


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
        "{}/gainers?apikey={}".format(FMP_API_BASE_URL, FMP_API_KEY)
    )


def get_earning_calendar(from_date=None, to_date=None):
    from_to_date = ""
    if from_date:
        from_to_date += "from={}&".format(from_date)
    if to_date:
        from_to_date += "to={}&".format(to_date)
    return _get_jsonparsed_data(
        "{}/earning_calendar?{}apikey={}".format(
            FMP_API_BASE_URL, from_to_date, FMP_API_KEY
        )
    )


def get_quotes(symbol_list):
    return _get_jsonparsed_data(
        "{}/quote/{}?apikey={}".format(
            FMP_API_BASE_URL, ",".join(symbol_list), FMP_API_KEY
        )
    )


def get_quote_short(symbol):
    return _get_jsonparsed_data(
        "{}/quote-short/{}?apikey={}".format(FMP_API_BASE_URL,
                                             symbol, FMP_API_KEY)
    )[0]


def get_daily_sma(symbol, period):
    return _get_jsonparsed_data(
        "{}/technical_indicator/daily/{}?period={}&type=sma&apikey={}".format(
            FMP_API_BASE_URL, symbol, period, FMP_API_KEY
        )
    )


def get_daily_rsi(symbol, period):
    return _get_jsonparsed_data(
        "{}/technical_indicator/daily/{}?period={}&type=rsi&apikey={}".format(
            FMP_API_BASE_URL, symbol, period, FMP_API_KEY
        )
    )


def get_intraday_sma(symbol, interval, period):
    return _get_jsonparsed_data(
        "{}/technical_indicator/{}/{}?period={}&type=sma&apikey={}".format(
            FMP_API_BASE_URL, interval, symbol, period, FMP_API_KEY
        )
    )


def get_market_hour():
    return _get_jsonparsed_data(
        "{}/market-hours?apikey={}".format(
            FMP_API_BASE_URL, FMP_API_KEY
        )
    )[0]
