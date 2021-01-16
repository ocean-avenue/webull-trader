import requests
from bs4 import BeautifulSoup

YF_GAINERS_URL = "https://finance.yahoo.com/gainers?count=100"


def _get_browser_headers():
    return {
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36",
        "referer": "http://finance.yahoo.com/",
        "Accept-Encoding": None,
    }


def get_most_gainers():
    session = requests.Session()
    res = session.get(YF_GAINERS_URL, headers=_get_browser_headers())
    sp = BeautifulSoup(res.text, "html.parser")
    most_gainers = []
    all_tr = sp.findAll("tr")
    for i in range(1, len(all_tr)):
        tr = all_tr[i]
        symbol = tr.find("a").contents[0]
        all_span = tr.findAll("span")
        change_percentage = all_span[2].contents[0]
        volume = all_span[3].contents[0]
        market_cap = all_span[4].contents[0]
        most_gainers.append(
            {
                "symbol": symbol,
                "change_percentage": change_percentage,
                "volume": volume,
                "market_cap": market_cap,
            }
        )
    return most_gainers