import json
from urllib.request import urlopen
from credentials.fmp import FMP_API_KEY

# https://financialmodelingprep.com/developer/docs
FMP_API_BASE_URL = "https://financialmodelingprep.com/api/v3"


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


def get_quote(symbol):
    return _get_jsonparsed_data(
        "{}/quote/{}?apikey={}".format(
            FMP_API_BASE_URL, symbol, FMP_API_KEY
        )
    )[0]


def get_quotes(symbol_list):
    return _get_jsonparsed_data(
        "{}/quote/{}?apikey={}".format(
            FMP_API_BASE_URL, ",".join(symbol_list), FMP_API_KEY
        )
    )


def batch_quotes(symbol_list):
    batch_symbol_list = []
    quote_list = []
    for symbol in symbol_list:
        batch_symbol_list.append(symbol)
        # batch 100 symbol request
        if len(batch_symbol_list) == 100:
            quotes = get_quotes(batch_symbol_list)
            quote_list = quote_list + quotes
            # reset batch symbol list
            batch_symbol_list = []
    # last batch symbol request
    if len(batch_symbol_list) > 0:
        quotes = get_quotes(batch_symbol_list)
        quote_list = quote_list + quotes
        # reset batch symbol list
        batch_symbol_list = []
    return quote_list


def get_quote_short(symbol):
    return _get_jsonparsed_data(
        "{}/quote-short/{}?apikey={}".format(FMP_API_BASE_URL,
                                             symbol, FMP_API_KEY)
    )[0]


def get_quotes_short(symbol_list):
    return _get_jsonparsed_data(
        "{}/quote-short/{}?apikey={}".format(
            FMP_API_BASE_URL, ",".join(symbol_list), FMP_API_KEY)
    )


def batch_quotes_short(symbol_list):
    batch_symbol_list = []
    quote_list = []
    for symbol in symbol_list:
        batch_symbol_list.append(symbol)
        # batch 100 symbol request
        if len(batch_symbol_list) == 100:
            quotes = get_quotes_short(batch_symbol_list)
            quote_list = quote_list + quotes
            # reset batch symbol list
            batch_symbol_list = []
    # last batch symbol request
    if len(batch_symbol_list) > 0:
        quotes = get_quotes_short(batch_symbol_list)
        quote_list = quote_list + quotes
        # reset batch symbol list
        batch_symbol_list = []
    return quote_list


def get_profile(symbol):
    profiles = _get_jsonparsed_data(
        "{}/profile/{}?apikey={}".format(
            FMP_API_BASE_URL, symbol, FMP_API_KEY
        )
    )
    if len(profiles) > 0:
        return profiles[0]
    return None


def get_profiles(symbol_list):
    return _get_jsonparsed_data(
        "{}/profile/{}?apikey={}".format(
            FMP_API_BASE_URL, ",".join(symbol_list), FMP_API_KEY
        )
    )


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


def get_news(symbol, count=20):
    return _get_jsonparsed_data(
        "{}/stock_news?tickers={}&limit={}&apikey={}".format(
            FMP_API_BASE_URL, symbol, count, FMP_API_KEY
        )
    )


def get_market_hour():
    return _get_jsonparsed_data(
        "{}/market-hours?apikey={}".format(
            FMP_API_BASE_URL, FMP_API_KEY
        )
    )[0]
