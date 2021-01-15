import json
from urllib.request import urlopen

FMP_API_BASE = "https://financialmodelingprep.com/api/v3"

FMP_API_KEY = "604558cf09f6b7db14f67dc13f007f8f"


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


def get_most_gainer_stock_companies():
    return _get_jsonparsed_data("{}/gainers?apikey={}".format(FMP_API_BASE, FMP_API_KEY))
